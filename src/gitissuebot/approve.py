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

# Github API URLs
USER_URL = "https://api.github.com/user"
ISSUES_URL = "https://api.github.com/repos/{repo}/issues?state=open&since={since}"


##~~ some helpers


def issue_filter(issue, ignored_labels=(), ignored_titles=()):
	"""
	Filters the given issue, returns True iff issue is neither a pull request nor has an ignored label or contains
	an ignored title

	:param issue: the issue to filter
	:param ignored_labels: list of ignored labels to check against
	:param ignored_titles: list of ignored titles to check against
	:return: true if issue matches the filter (see above), false otherwise
	"""

	not_pull_request = not "pull_request" in issue
	not_ignored_label = len(set(ignored_labels).intersection(set(map(lambda x: x["name"], issue["labels"])))) == 0

	not_ignored_title = True
	for ignored_title in ignored_titles:
		if ignored_title.lower() in issue["title"].lower():
			not_ignored_title = False
			break

	return not_pull_request and not_ignored_label and not_ignored_title


def validator(issue, headers, config):
	"""
	Validates the given issue. Checks the issue's body and all comments on the issue made by the issue's author
	for the trigger phrase.

	:param issue: the issue to validate
	:param headers: headers to use for requests against API
	:param config: config to use
	:return: true if issue validates, false otherwise
	"""
	if config["phrase"].lower() in issue["body"].lower():
		return True

	author = issue["user"]["id"]

	if issue["comments"] > 0:
		r = requests.get(issue["comments_url"], headers=headers)
		comments = r.json()
		for comment in comments:
			if comment["user"]["id"] == author and config["phrase"].lower() in comment["body"].lower():
				return True

	return False


def convert_to_internal(issue):
	"""
	Converts the issue to an internal (more flattened) representation.

	Converts created and updated fields to datetime objects and flattens labels and author.

	:param issue: the issue to convert
	:return: the converted issue
	"""

	return {
		"title": issue["title"],
		"author": issue["user"]["login"],
		"created_str": issue["created_at"],
		"created": dateutil.parser.parse(issue["created_at"]),
		"updated_str": issue["updated_at"],
		"updated": dateutil.parser.parse(issue["updated_at"]),
		"labels": map(lambda x: x["name"], issue["labels"]),
		"comments": issue["comments"],
		"comments_url": issue["comments_url"],
		"url": issue["url"]
	}


def get_bot_id(headers):
	"""
	Retrieves the id of the bot.

	:param headers: headers to use for requests against API
	:return: the bot's user id
	"""

	r = requests.get(USER_URL, headers=headers)
	myself = r.json()
	return myself["id"]


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
	if not dryrun:
		requests.post(issue["comments_url"], headers=headers, data=json.dumps({"body": personalized_reminder}))
	else:
		print("\t\tPOST %s to add reminder comment" % issue["comments_url"])

	# label the issue if configured
	if "label" in config and config["label"]:
		current_labels = list(issue["labels"])
		current_labels.append(config["label"])

		if not dryrun:
			requests.patch(issue["url"], headers=headers, data=json.dumps({"labels": current_labels}))
		else:
			print("\t\tPATCH %s to set labels=%r" % (issue["url"], current_labels))



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
	if not dryrun:
		requests.patch(issue["url"], headers=headers, data=json.dumps({"labels": current_labels}))
	else:
		print("\t\tPATCH %s to set labels=%r" % (issue["url"], current_labels))


def close_issue(issue, headers, config, dryrun):
	"""
	Closes an issue.

	:param issue: the issue to close
	:param headers: headers to use for requests against API
	:param config: config to use
	:param dryrun: whether to only simulate the writing API calls
	"""

	# post a comment if configured
	if "closing" in config and config["closing"]:
		if not dryrun:
			requests.post(issue["comments_url"], headers=headers, data=json.dumps({"body": config["closing"]}))
		else:
			print("\t\tPOST %s to add closing comment" % issue["comments_url"])

	# close the issue
	if not dryrun:
		requests.patch(issue["url"], headers=headers, data=json.dumps({"state": "closed"}))
	else:
		print("\t\tPATCH %s to set state=closed" % issue["url"])


def check_issues(config, file=None, dryrun=False):

	# prepare headers
	headers = {"Authorization": "token %s" % config["token"]}

	# calculate grace period cutoff date, if grace period and label are configured
	if config["grace_period"] >= 0 and "label" in config and config["label"]:
		grace_period_cutoff = datetime.datetime.utcnow().replace(tzinfo=dateutil.tz.tzutc()) - datetime.timedelta(config["grace_period"])
		bot_user_id = get_bot_id(headers)
		since = min(config["since"], grace_period_cutoff)
	else:
		grace_period_cutoff = None
		bot_user_id = None
		since = config["since"]

	# retrieve issues to process
	url = ISSUES_URL.format(repo=config["repo"], since=since.isoformat())
	r = requests.get(url, headers=headers)
	issues = filter(lambda x: issue_filter(x, ignored_labels=config["ignored_labels"], ignored_titles=config["ignored_titles"]), r.json())
	print("Found %d issues to process..." % len(issues))

	# process each issue
	for issue in issues:
		internal = convert_to_internal(issue)

		print("Processing \"%s\" by %s (created %s, last updated %s)" % (internal["title"], internal["author"], internal["created_str"], internal["updated_str"]))

		valid = validator(issue, headers, config)

		if "label" in config and config["label"] and config["label"] in internal["labels"]:
			# issue is currently labeled as incomplete, let's see if the information has been added or if it's still missing
			if valid:
				# issue is now valid => remove the label marking it as lacking information
				print("\t... author updated ticket with information, marking valid")
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
						print("\t... information still missing after grace period, closing the issue")
						close_issue(internal, headers, config, dryrun)

		elif internal["created"] >= config["since"] and not valid:
			# issue was created since last run and is invalid => add a friendly comment and label the issue correspondingly
			print("\t... reminding author of information to include")
			add_reminder(internal, headers, config, dryrun)

	if file is not None and not dryrun:
		# we are using a config file, so we save the current date and time for the next run
		update_config(file)


##~~ config handling


def load_config(file):
	"""
	Loads the config from the file

	:param file: the file from which to load the config
	:return: the loaded config represented as a dictionary, might be empty if config file was not found or empty
	"""
	import yaml
	import os

	def datetime_constructor(loader, node):
		return dateutil.parser.parse(node.value)
	yaml.add_constructor(u'tag:yaml.org,2002:timestamp', datetime_constructor)

	config = None
	if file is not None and os.path.exists(file) and os.path.isfile(file):
		with open(file, "r") as f:
			config = yaml.safe_load(f)

	if config is None:
		config = {}

	return config


def validate_config(config):
	"""
	Makes sure the given config is valid, filling in default values and sanitizing existing values were necessary and
	exiting the application if mandatory parameters are not given.

	:param config: the config to validate
	"""
	import sys

	# check for mandatory values
	if not "token" in config or not config["token"]:
		print("Token must be defined", file=sys.stderr)
		sys.exit(-1)
	if not "repo" in config or not config["repo"]:
		print("Repo must be defined", file=sys.stderr)
		sys.exit(-1)
	if not "reminder" in config or not config["reminder"]:
		print("Reminder text must be defined", file=sys.stderr)
		sys.exit(-1)

	# set default values were necessary
	if not "since" in config or not config["since"]:
		config["since"] = datetime.datetime.utcnow()
	if not "grace_period" in config or config["grace_period"] is None:
		config["grace_period"] = 14
	if not "closing" in config or not config["closing"]:
		config["closing"] = None
	if not "ignored_labels" in config:
		config["ignored_labels"] = ()
	if not "ignored_titles" in config:
		config["ignored_titles"] = ()
	if not "dryrun" in config:
		config["dryrun"] = False
	if not "phrase" in config or not config["phrase"]:
		config["phrase"] = "I love cookies"

	# sanitizing
	if config["since"].tzinfo is None:
		config["since"] = config["since"].replace(tzinfo=dateutil.tz.tzutc())


def update_config(filename, since=datetime.datetime.utcnow()):
	import yaml
	import os
	import shutil

	if filename is not None and os.path.exists(filename) and os.path.isfile(filename):
		# load config from file
		with open(filename, "r") as f:
			config = yaml.safe_load(f)
		if config is None:
			return

		# update since
		config["since"] = since.replace(tzinfo=dateutil.tz.tzutc())

		# write back the config
		tmpfilename = filename + ".tmp"
		try:
			with open(tmpfilename, "w") as f:
				yaml.safe_dump(config, f, default_flow_style=False, indent="    ", allow_unicode=True)
			shutil.copyfile(tmpfilename, filename)
		finally:
			os.remove(tmpfilename)

		print("Saved current date and time for next run")


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
	parser.add_argument("-s", "--since", action="store", dest="since", type=dateutil.parser.parse,
						help="Only validate issues created or updated after this ISO8601 date time, defaults to now")
	parser.add_argument("-p", "--phrase", action="store", dest="phrase",
						help="Trigger phrase to look for in comments to approve, defaults to \"I love cookies\"")
	parser.add_argument("-g", "--grace", action="store", dest="grace_period", type=int,
						help="Grace period in days after which to close issues lacking information, set to -1 to never autoclose, defaults to 14 days. Note: Automatic closing only works if label is set")
	parser.add_argument("-l", "--label", action="store", dest="label",
						help="Label to apply to issues missing information, can be left out if such issues are not be labeled specially. Defaults to not set. Note: Specified label must exist in the targeted repo!")
	parser.add_argument("--ignored-labels", action="store", dest="ignored_labels",
						help="Comma-separated list of labels tagging issues to ignore during processing (e.g. feature requests), defaults to an empty list")
	parser.add_argument("--ignored-titles", action="store", dest="ignored_titles",
						help="Comma-separated list of issue title parts which should cause the issue to be ignored (e.g. \"[Feature Request]\"), defaults to an empty list")
	parser.add_argument("--closing", action="store", dest="closing",
						help="Text of comment when closing an issue after the grace period, defaults to not set and thus no comment being posted upon closing.")
	parser.add_argument("--dry-run", action="store_true", dest="dryrun",
						help="Just print what would be done without actually doing it")

	# parse CLI arguments
	args = parser.parse_args()

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
	if args.reminder is not None:
		config["reminder"] = args.reminder
	if args.closing is not None:
		config["closing"] = args.closing
	config["dryrun"] = config["dryrun"] or args.dryrun

	# validate the config
	validate_config(config)

	# check existing issues
	check_issues(config, file=args.config, dryrun=config["dryrun"])


if __name__ == "__main__":
	main()

