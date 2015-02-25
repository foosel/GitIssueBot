# coding=utf-8
from __future__ import print_function, absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 Gina Häußge - Released under terms of the AGPLv3 License"

import requests
import json
import sys
import datetime
import dateutil.parser

from .util import get_issues, load_config, update_config, no_pullrequests, convert_to_internal, setup_logging, print_version

import logging
logger = logging.getLogger(__name__)


##~~ process issues


def apply_label(label, issue, headers, dryrun=False):
	current_labels = list(issue["labels"])
	current_labels.append(label)

	logger.debug("-> Adding a label via PATCH %s, labels=%r" % (issue["url"], current_labels))
	if not dryrun:
		requests.patch(issue["url"], headers=headers, data=json.dumps({"labels": current_labels}))


def process_issues(config, file=None, dryrun=False):
	# prepare headers
	headers = {"Authorization": "token %s" % config["token"]}

	mappings = config["mappings"]
	if config["ignore_case"]:
		mappings = map(lambda data: dict(tag=data["tag"].lower(), label=data["label"]), mappings)

	since = config["since"]

	# retrieve issues to process
	logger.info("Fetching all issues")
	issues = get_issues(config["token"], config["repo"], since=since, issue_filter=no_pullrequests, converter=convert_to_internal)
	logger.info("Found %d issues to process..." % len(issues))

	for issue in issues:
		logger.info(u"Processing \"%s\" by %s (created %s, last updated %s)" % (issue["title"], issue["author"], issue["created_str"], issue["updated_str"]))

		try:
			for mapping in mappings:
				tag = mapping["tag"]
				label = mapping["label"]
				title = issue["title"].lower() if config["ignore_case"] else issue["title"]

				if tag in title and not label in issue["labels"]:
					logger.info("... applying label {label}".format(label=label))
					apply_label(label, issue, headers, dryrun=dryrun)
		except:
			logger.exception("Exception while processing issue")

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
	if not "mappings" in config or not config["mappings"]:
		logger.error("At least one mapping must be defined")
		sys.exit(-1)

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
	if args.mappings is not None:
		config["mappings"] = args.mappings
	config["ignore_case"] = config["ignore_case"] if "ignore_case" in config and config["ignore_case"] else False or args.ignore_case
	config["dryrun"] = config["dryrun"] if "dryrun" in config and config["dryrun"] else False or args.dryrun
	config["debug"] = config["debug"] if "debug" in config and config["debug"] else False or args.debug

	# validate the config
	validate_config(config)

	# setup logger
	setup_logging(debug=config["debug"])

	# process existing issues
	process_issues(config, file=args.config, dryrun=config["dryrun"])

def argparser(parser=None):
	if parser is None:
		import argparse
		parser = argparse.ArgumentParser(prog="gitissuebot-approve")

	def label_dict(raw):
		if not "=" in raw:
			raise argparse.ArgumentTypeError("{raw} doesn't follow the expected format '<tag>=<label>'".format(raw=raw))

		tag, label = raw.split("=", 2)
		return dict(tag=tag, label=label)

	# prepare CLI argument parser
	parser.add_argument("-c", "--config", action="store", dest="config",
	                    help="The config file to use")
	parser.add_argument("-t", "--token", action="store", dest="token",
	                    help="The token to use, must be defined either on CLI or via config")
	parser.add_argument("-r", "--repo", action="store", dest="repo",
	                    help="The github repository to use, must be defined either on CLI or via config")
	parser.add_argument("-s", "--since", action="store", dest="since", type=dateutil.parser.parse,
	                    help="Only validate issues created or updated after this ISO8601 date time, defaults to now")
	parser.add_argument("-m", "--map", action="append", dest="mappings", type=label_dict,
	                    help="Tag-label-mappings to use. Expected format is '<tag>=<label>'")
	parser.add_argument("-i", "--ignore-case", action="store_true", dest="ignore_case",
	                    help="Ignore case when matching the title snippets")
	parser.add_argument("--dry-run", action="store_true", dest="dryrun",
	                    help="Just print what would be done without actually doing it")
	parser.add_argument("-v", "--version", action="store_true", dest="version",
	                    help="Print the version and exit")
	parser.add_argument("--debug", action="store_true", dest="debug",
	                    help="Enable debug logging")

	return parser

if __name__ == "__main__":
	main()