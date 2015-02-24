# coding=utf-8
from __future__ import print_function

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 Gina Häußge - Released under terms of the AGPLv3 License"

import requests
import json
import dateutil.parser, dateutil.tz
import time
import datetime
import sys

if __package__ is None:
	import sys
	from os import path
	sys.path.append( path.dirname( path.dirname( path.abspath(__file__) ) ) )
	from util import get_issues, load_config, update_config, get_bot_id, convert_to_internal, no_pullrequests, setup_logging
else:
	from .util import get_issues, load_config, update_config, get_bot_id, convert_to_internal, no_pullrequests, setup_logging


import logging
logger = logging.getLogger(__name__)


class OldPhrase(Exception):
	pass


##~~ some helpers


def validator(issue, headers, config):
	"""
	Validates the given issue. Checks the issue's body and all comments on the issue made by the issue's author
	for the trigger phrase.

	:param issue: the issue to validate
	:param headers: headers to use for requests against API
	:param config: config to use
	:return: true if issue validates, false otherwise
	"""

	ignored_label = len(set(config["ignored_labels"]).intersection(set(map(lambda x: x["name"], issue["labels"])))) > 0
	if ignored_label:
		return True

	for ignored_title in config["ignored_titles"]:
		if ignored_title.lower() in issue["title"].lower():
			return True

	lower_body = issue["body"].lower()
	if config["phrase"].lower() in lower_body:
		return True
	elif len(config["past_phrases"]) > 0:
		for phrase in config["past_phrases"]:
			if phrase.lower() in lower_body:
				raise OldPhrase()

	author = issue["user"]["id"]

	if issue["comments"] > 0:
		r = requests.get(issue["comments_url"], headers=headers)
		comments = r.json()
		for comment in comments:
			if comment["user"]["id"] == author and config["phrase"].lower() in comment["body"].lower():
				return True

	return False


##~~ issue processing


def add_reminder(issue, headers, config, dryrun):
	"""
	Adds a reminder to the given issue.

	:param issue: the issue to add a reminder to
	:param headers: headers to use for requests against API
	:param config: config to use
	:param dryrun: whether to only simulate the writing API calls
	"""

	until = datetime.datetime.now() + datetime.timedelta(config["grace_period"])
	personalized_reminder = config["reminder"].format(author=issue["author"], until=until.strftime("%Y-%m-%d %H:%M"))

	# post a comment
	logger.debug("-> Adding a reminder comment via POST %s" % issue["comments_url"])
	if not dryrun:
		requests.post(issue["comments_url"], headers=headers, data=json.dumps({"body": personalized_reminder}))

	# label the issue if configured
	if "label" in config and config["label"]:
		current_labels = list(issue["labels"])
		current_labels.append(config["label"])

		logger.debug("-> Marking issues as invalid via PATCH %s, labels=%r" % (issue["url"], current_labels))
		if not dryrun:
			requests.patch(issue["url"], headers=headers, data=json.dumps({"labels": current_labels}))


def add_oldphrasehint(issue, headers, config, dryrun):
	"""
	Adds a hint that the used trigger phrase has been marked as obsolete.

	:param issue: the issue to add a reminder to
	:param headers: headers to use for requests against API
	:param config: config to use
	:param dryrun: whether to only simulate the writing API calls
	"""

	personalized_hint = config["newphrase"].format(author=issue["author"])

	# post a comment
	logger.debug("-> Adding a old phrase hint comment via POST %s" % issue["comments_url"])
	if not dryrun:
		requests.post(issue["comments_url"], headers=headers, data=json.dumps({"body": personalized_hint}))


def mark_issue_valid(issue, headers, config, dryrun):
	"""
	Marks a (formerly invalidated) issue as valid.

	:param issue: the issue to mark as valid
	:param headers: headers to use for requests against API
	:param config: config to use
	:param dryrun: whether to only simulate the writing API calls
	"""

	if not "label" in config or not config["label"]:
		# no label configured, nothing to do
		return

	current_labels = list(issue["labels"])
	current_labels.remove(config["label"])

	logger.debug("-> Marking issue valid via PATCH %s, labels=%r" % (issue["url"], current_labels))
	if not dryrun:
		requests.patch(issue["url"], headers=headers, data=json.dumps({"labels": current_labels}))


def close_issue(issue, headers, config, dryrun):
	"""
	Closes an issue after the grace period. Uses the text defined for ``closing`` in the configuration for the
	closing comment.

	:param issue: the issue to close
	:param headers: headers to use for requests against API
	:param config: config to use
	:param dryrun: whether to only simulate the writing API calls
	"""

	body = None
	if "closing" in config and config["closing"]:
		body = config["closing"]

	_close(issue, headers, body, dryrun)


def directly_close_issue(issue, headers, config, dryrun):
	"""
	Closes an issue directly. Uses the text defined for ``closingnow`` in the configuration for the closing comment.

	:param issue: the issue to close
	:param headers: headers to use for requests against API
	:param config: config to use
	:param dryrun: whether to only simulate the writing API calls
	"""

	body = None
	if "closingnow" in config and config["closingnow"]:
		body = config["closingnow"].format(author=issue["author"])

	_close(issue, headers, body, dryrun)


def _close(issue, headers, body, dryrun):
	if body is not None:
		logger.debug("-> Adding a closing comment via POST %s" % issue["comments_url"])
		if not dryrun:
			requests.post(issue["comments_url"], headers=headers, data=json.dumps({"body": body}))

	# close the issue
	logger.debug("-> Closing issue via PATCH %s, state=closed" % issue["url"])
	if not dryrun:
		requests.patch(issue["url"], headers=headers, data=json.dumps({"state": "closed"}))


def check_issues(config, file=None, dryrun=False):

	# prepare headers
	headers = {"Authorization": "token %s" % config["token"]}

	# calculate grace period cutoff date, if grace period and label are configured
	if config["grace_period"] >= 0 and "label" in config and config["label"]:
		grace_period_cutoff = datetime.datetime.utcnow().replace(tzinfo=dateutil.tz.tzutc()) - (datetime.timedelta(config["grace_period"] + 1))
		bot_user_id = get_bot_id(headers)
		since = min(config["since"], grace_period_cutoff)
	else:
		grace_period_cutoff = None
		bot_user_id = None
		since = config["since"]

	close_directly = config["close_directly"]

	# retrieve issues to process
	logger.info("Fetching all issues since %s" % since.isoformat())
	issues = get_issues(config["token"], config["repo"], issue_filter=no_pullrequests, since=since)
	logger.info("Found %d issues to process..." % len(issues))

	# process each issue
	for issue in issues:
		internal = convert_to_internal(issue)

		logger.info(u"Processing \"%s\" by %s (created %s, last updated %s)" % (internal["title"], internal["author"], internal["created_str"], internal["updated_str"]))

		try:
			try:
				valid = validator(issue, headers, config)
			except OldPhrase:
				add_oldphrasehint(internal, headers, config, dryrun)
				valid = True

			if "label" in config and config["label"] and config["label"] in internal["labels"]:
				# issue is currently labeled as incomplete, let's see if the information has been added or if it's still missing
				if valid:
					# issue is now valid => remove the label marking it as lacking information
					logger.info("... author updated ticket with information, marking valid")
					mark_issue_valid(internal, headers, config, dryrun)

				elif grace_period_cutoff is not None:
					# issue is invalid, let's see if the grace period for this issue has been exceeded and we can close it

					# find the last comment made by the bot
					r = requests.get(internal["comments_url"], headers=headers)
					comments = r.json()
					bot_comment = None
					for comment in comments:
						if comment["user"]["id"] == bot_user_id:
							bot_comment = comment

					if bot_comment is not None:
						# we found the last comment by our bot, let's check if the grace period is over
						comment_creation_datetime = dateutil.parser.parse(bot_comment["created_at"])

						if grace_period_cutoff > comment_creation_datetime:
							# grace period is over, let's post a comment and close the issue
							logger.info("... information still missing after grace period, closing the issue")
							close_issue(internal, headers, config, dryrun)

			elif internal["created"] >= config["since"] and not valid:
				# issue was created since last run and is invalid
				if close_directly:
					# we close tickets directly => add a comment and close the ticket
					logger.info("... information is missing, closing the ticket")
					directly_close_issue(internal, headers, config, dryrun)
				else:
					# we don't close tickets directly => add a friendly comment and label the issue correspondingly
					logger.info("... reminding author of information to include")
					add_reminder(internal, headers, config, dryrun)
		except:
			logger.exception("Exception while processing issues")

	if file is not None and not dryrun:
		# we are using a config file, so we save the current date and time for the next run
		update_config(file)


##~~ config handling


def validate_config(config):
	"""
	Makes sure the given config is valid, filling in default values and sanitizing existing values were necessary and
	exiting the application if mandatory parameters are not given.

	:param config: the config to validate
	"""
	import sys

	# check for mandatory values
	if not "token" in config or not config["token"]:
		logger.error("Token must be defined")
		sys.exit(-1)
	if not "repo" in config or not config["repo"]:
		logger.error("Repo must be defined")
		sys.exit(-1)
	if not "reminder" in config or not config["reminder"]:
		logger.error("Reminder text must be defined")
		sys.exit(-1)

	# set default values were necessary
	if not "since" in config or not config["since"]:
		config["since"] = datetime.datetime.utcnow()
	if not "grace_period" in config or config["grace_period"] is None:
		config["grace_period"] = 14
	if not "close_directly" in config or config["close_directly"] is None:
		config["close_directly"] = False
	if not "closing" in config or not config["closing"]:
		config["closing"] = None
	if not "closingnow" in config or not config["closingnow"]:
		config["closingnow"] = None
	if not "ignored_labels" in config:
		config["ignored_labels"] = ()
	if not "ignored_titles" in config:
		config["ignored_titles"] = ()
	if not "dryrun" in config:
		config["dryrun"] = False
	if not "phrase" in config or not config["phrase"]:
		config["phrase"] = "I love cookies"
	if not "debug" in config or config["debug"] is None:
		config["debug"] = False

	if not "past_phrases" in config or not config["past_phrases"]:
		config["past_phrases"] = []
	else:
		if not "newphrase" in config or not config["newphrase"]:
			logger.info("New phrase text must be defined", file=sys.stderr)

	# sanitizing
	if config["since"].tzinfo is None:
		config["since"] = config["since"].replace(tzinfo=dateutil.tz.tzutc())


##~~ CLI


def main():
	import argparse

	# prepare CLI argument parser
	parser = argparse.ArgumentParser(prog="gitissuebot-approve")
	parser.add_argument("-c", "--config", action="store", dest="config",
						help="The config file to use")
	parser.add_argument("-t", "--token", action="store", dest="token",
						help="The token to use, must be defined either on CLI or via config")
	parser.add_argument("-r", "--repo", action="store", dest="repo",
						help="The github repository to use, must be defined either on CLI or via config")
	parser.add_argument("--reminder", action="store", dest="reminder",
						help="Text of comment to remind people of missing information, must be defined either on CLI or via config")
	parser.add_argument("--newphrase", action="store", dest="newphrase",
						help="Text of comment to approve comment but hint at new trigger phrase, must be defined if past phrases are defined, either on CLI or via config")
	parser.add_argument("-s", "--since", action="store", dest="since", type=dateutil.parser.parse,
						help="Only validate issues created or updated after this ISO8601 date time, defaults to now")
	parser.add_argument("-p", "--phrase", action="store", dest="phrase",
						help="Trigger phrase to look for in comments to approve, defaults to \"I love cookies\"")
	parser.add_argument("-P", "--past-phrases", action="store", dest="past_phrases",
						help="Past trigger phrases to look for in comments to approve, defaults to empty list")
	parser.add_argument("-g", "--grace", action="store", dest="grace_period", type=int,
						help="Grace period in days after which to close issues lacking information, set to -1 to never autoclose, defaults to 14 days. Note: Automatic closing only works if label is set")
	parser.add_argument("-k", "--close", action="store_true", dest="close_directly",
						help="Directly close invalid tickets instead of applying grace period")
	parser.add_argument("-l", "--label", action="store", dest="label",
						help="Label to apply to issues missing information, can be left out if such issues are not be labeled specially. Defaults to not set. Note: Specified label must exist in the targeted repo!")
	parser.add_argument("--ignored-labels", action="store", dest="ignored_labels",
						help="Comma-separated list of labels tagging issues to ignore during processing (e.g. feature requests), defaults to an empty list")
	parser.add_argument("--ignored-titles", action="store", dest="ignored_titles",
						help="Comma-separated list of issue title parts which should cause the issue to be ignored (e.g. \"[Feature Request]\"), defaults to an empty list")
	parser.add_argument("--closing", action="store", dest="closing",
						help="Text of comment when closing an issue after the grace period, defaults to not set and thus no comment being posted upon closing.")
	parser.add_argument("--closingnow", action="store", dest="closingnow",
						help="Text of comment when closing an issue directly, defaults to not set and thus no comment being posted upon closing.")
	parser.add_argument("--dry-run", action="store_true", dest="dryrun",
						help="Just print what would be done without actually doing it")
	parser.add_argument("-v", "--version", action="store_true", dest="version",
						help="Print the version and exit")
	parser.add_argument("--debug", action="store_true", dest="debug",
	                    help="Enable debug logging")

	# parse CLI arguments
	args = parser.parse_args()

	# if only version is to be printed, do so and exit
	if args.version:
		from gitissuebot import _version
		logger.info(_version.get_versions()["version"])
		sys.exit(0)

	# merge config (if given) and CLI parameters
	config = load_config(args.config)
	if args.token is not None:
		config["token"] = args.token
	if args.repo is not None:
		config["repo"] = args.repo
	if args.since is not None:
		config["since"] = args.since
	if args.label is not None:
		config["label"] = args.label
	if args.ignored_labels is not None:
		config["ignored_labels"] = filter(lambda x: x is not None and len(x) > 0, map(str.strip, args.ignored_labels.split(",")))
	if args.ignored_titles is not None:
		config["ignored_titles"] = filter(lambda x: x is not None and len(x) > 0, map(str.strip, args.ignored_titles.split(",")))
	if args.grace_period is not None:
		config["grace_period"] = args.grace_period
	if args.phrase is not None:
		config["phrase"] = args.phrase
	if args.past_phrases is not None:
		config["past_phrases"] = filter(lambda x: x is not None and len(x) > 0, map(str.strip, args.past_phrases.split(",")))
	if args.reminder is not None:
		config["reminder"] = args.reminder
	if args.closing is not None:
		config["closing"] = args.closing
	if args.closingnow is not None:
		config["closingnow"] = args.closingnow
	config["close_directly"] = config["close_directly"] if "close_directly" in config else False or args.close_directly
	config["dryrun"] = config["dryrun"] if "dryrun" in config else False or args.dryrun
	config["debug"] = config["debug"] if "debug" in config else False or args.debug

	# validate the config
	validate_config(config)

	# setup logger
	setup_logging(debug=config["debug"])

	# check existing issues
	check_issues(config, file=args.config, dryrun=config["dryrun"])


if __name__ == "__main__":
	main()

