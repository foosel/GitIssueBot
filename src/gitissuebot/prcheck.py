# coding=utf-8
from __future__ import print_function, absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2016 Gina Häußge - Released under terms of the AGPLv3 License"

import requests
import json
import sys
import datetime
import dateutil.parser
import re

from .util import get_prs, load_config, update_config, convert_to_internal_pr, convert_to_internal, setup_logging, print_version

import logging
logger = logging.getLogger(__name__)


##~~ helpers

def valid(pr, config):
	targets = config["targets"]
	blacklisted_targets = config["blacklisted_targets"]
	sources = config["sources"]
	blacklisted_sources = config["blacklisted_sources"]
	if config["ignore_case"]:
		targets = map(lambda x: x.lower(), targets)
		blacklisted_targets = map(lambda x: x.lower(), blacklisted_targets)
		sources = map(lambda x: x.lower(), sources)
		blacklisted_sources = map(lambda x: x.lower(), blacklisted_sources)

	not_in_targets = len(targets) > 0 and all(map(lambda target: target != pr["target_branch"], targets))
	in_blacklisted_targets = len(blacklisted_targets) > 0 and any(map(lambda target: target == pr["target_branch"], blacklisted_targets))
	not_in_sources = len(sources) > 0 and all(map(lambda source: source != pr["source_branch"], sources))
	in_blacklisted_sources = len(blacklisted_sources) > 0 and any(map(lambda source: source == pr["source_branch"], blacklisted_sources))
	empty_body = pr["body"] is None or pr["body"].strip() == ""
	invalid_title = pr["title"] is None or not config["title_compiled_regex"].match(pr["title"])
	problems = []

	if not_in_targets:
		problems.append("invalid_target")
	if in_blacklisted_targets:
		problems.append("blacklisted_target")
	if not_in_sources:
		problems.append("invalid_source")
	if in_blacklisted_sources:
		problems.append("blacklisted_source")
	if empty_body:
		problems.append("empty_body")
	if invalid_title:
		problems.append("invalid_title")

	return problems

def add_reminder(pr, config, problems, dryrun=False):
	# prepare headers
	headers = {"Authorization": "token %s" % config["token"]}

	texts = config["problems"]
	problem_texts = []
	for problem in problems:
		if problem not in texts:
			continue

		def format_branch_list(branches):
			return ", ".join(map(lambda x: "`{}`".format(x), branches))

		problem_texts.append(texts[problem].format(source_branch=pr["source_branch"],
		                                           target_branch=pr["target_branch"],
		                                           source_repo=pr["source_repo"],
		                                           target_repo=pr["target_repo"],
		                                           sources=format_branch_list(config["sources"]),
		                                           targets=format_branch_list(config["targets"]),
		                                           blacklisted_sources=format_branch_list(config["blacklisted_sources"]),
		                                           blacklisted_targets=format_branch_list(config["blacklisted_targets"])))

	personalized_reminder = config["reminder"].format(author=pr["author"],
		                                              source_repo=pr["source_repo"],
		                                              target_repo=pr["target_repo"],
	                                                  source_branch=pr["source_branch"],
	                                                  target_branch=pr["target_branch"],
	                                                  problems="\n".join(problem_texts))

	# post a comment
	logger.debug("-> Adding a reminder comment via POST %s" % pr["comments_url"])
	if not dryrun:
		requests.post(pr["comments_url"], headers=headers, data=json.dumps({"body": personalized_reminder}))

	# label the issue if configured
	if "label" in config and config["label"]:
		try:
			r = requests.get(pr["issue_url"], headers=headers)
			issue = convert_to_internal(r.json())
			current_labels = list(issue["labels"])
			current_labels.append(config["label"])

			logger.debug("-> Labeling PR via PATCH %s, labels=%r" % (pr["issue_url"], current_labels))
			if not dryrun:
				requests.patch(pr["issue_url"], headers=headers, data=json.dumps({"labels": current_labels}))
		except:
			logger.exception("Error while labeling PR #{}".format(pr["id"]))


##~~ process issues

def process_prs(config, file=None, dryrun=False):
	headers = {"Authorization": "token %s" % config["token"]}

	if dryrun:
		logger.info("THIS IS A DRYRUN")

	# retrieve issues to process
	logger.info("Fetching all PRs")

	def convert_pr(raw):
		pr = convert_to_internal_pr(raw)

		try:
			r = requests.get(pr["issue_url"], headers=headers)
			issue = convert_to_internal(r.json())
			pr["labels"] = issue["labels"]
		except:
			logger.exception("Error while retrieving labels for PR #{}".format(pr["id"]))
			pr["labels"] = []

		return pr

	prs = get_prs(config["token"], config["repo"], converter=convert_pr)
	logger.info("Found %d PRs to process..." % len(prs))

	for pr in prs:
		logger.info(u"Processing \"%s\" by %s (created %s, last updated %s)" % (pr["title"], pr["author"], pr["created_str"], pr["updated_str"]))

		if config["since"] > pr["created"]:
			logger.info("... too old, skipping")
			continue
		if "label" in config and config["label"] and config["label"] in pr["labels"]:
			logger.info("... already labeled, skipping")
			continue

		problems = valid(pr, config)
		if problems:
			logger.info("... reminding author of information to include: %s", str(problems))
			add_reminder(pr, config, problems, dryrun=dryrun)

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

	if not "targets" in config or not config["targets"]:
		config["targets"] = []
	if not "blacklisted_targets" in config or not config["blacklisted_targets"]:
		config["blacklisted_targets"] = []
	if not "sources" in config or not config["sources"]:
		config["sources"] = []
	if not "blacklisted_sources" in config or not config["blacklisted_sources"]:
		config["blacklisted_sources"] = []
	if not "since" in config or not config["since"]:
		config["since"] = datetime.datetime.utcnow()
	if not "ignore_case" in config or config["ignore_case"] is None:
		config["ignore_case"] = False
	if not "debug" in config or config["debug"] is None:
		config["debug"] = False


##~~ CLI


def main(args=None):
	if args is None:
		# parse CLI arguments
		parser = argparser()
		args = parser.parse_args()

	# if only version is to be printed, do so and exit
	if args.version:
		print_version()

	# merge config (if given) and CLI parameters
	config = load_config(args.config)
	if args.token is not None:
		config["token"] = args.token
	if args.repo is not None:
		config["repo"] = args.repo
	if args.since is not None:
		config["since"] = args.since
	if args.targets is not None:
		config["targets"] = args.targets
	if args.blacklisted_targets is not None:
		config["blacklisted_targets"] = args.blacklisted_targets
	if args.sources is not None:
		config["sources"] = args.sources
	if args.blacklisted_sources is not None:
		config["blacklisted_sources"] = args.blacklisted_sources
	config["title_compiled_regex"] = re.compile(config["title_regex"] if "title_regex" in config else '.*')
	config["ignore_case"] = config["ignore_case"] if "ignore_case" in config and config["ignore_case"] else False or args.ignore_case
	config["dryrun"] = config["dryrun"] if "dryrun" in config and config["dryrun"] else False or args.dryrun
	config["debug"] = config["debug"] if "debug" in config and config["debug"] else False or args.debug

	# validate the config
	validate_config(config)

	# setup logger
	setup_logging(debug=config["debug"])

	# process existing issues
	try:
		process_prs(config, file=args.config, dryrun=config["dryrun"])
	except:
		logger.exception("Error during execution")
		sys.exit(-1)

def argparser(parser=None):
	if parser is None:
		import argparse
		parser = argparse.ArgumentParser(prog="gitissuebot-approve")

	# prepare CLI argument parser
	parser.add_argument("-c", "--config", action="store", dest="config",
	                    help="The config file to use")
	parser.add_argument("-t", "--token", action="store", dest="token",
	                    help="The token to use, must be defined either on CLI or via config")
	parser.add_argument("-r", "--repo", action="store", dest="repo",
	                    help="The github repository to use, must be defined either on CLI or via config")
	parser.add_argument("-s", "--since", action="store", dest="since", type=dateutil.parser.parse,
	                    help="Only validate issues created or updated after this ISO8601 date time, defaults to now")
	parser.add_argument("--target", action="append", dest="targets", type=list,
	                    help="Target branches for PRs that must match for the PR to be considered valid")
	parser.add_argument("--notarget", action="append", dest="blacklisted_targets", type=list,
	                    help="Target branches for PRs that must not match for the PR to be considered valid")
	parser.add_argument("--source", action="append", dest="sources", type=list,
	                    help="Source branches for PRs that must match for the PR to be considered valid")
	parser.add_argument("--nosource", action="append", dest="blacklisted_sources", type=list,
	                    help="Source branches for PRs that must not match for the PR to be considered valid")
	parser.add_argument("-i", "--ignore-case", action="store_true", dest="ignore_case",
	                    help="Ignore case when matching branch names")
	parser.add_argument("--dry-run", action="store_true", dest="dryrun",
	                    help="Just print what would be done without actually doing it")
	parser.add_argument("-v", "--version", action="store_true", dest="version",
	                    help="Print the version and exit")
	parser.add_argument("--debug", action="store_true", dest="debug",
	                    help="Enable debug logging")

	return parser

if __name__ == "__main__":
	main()
