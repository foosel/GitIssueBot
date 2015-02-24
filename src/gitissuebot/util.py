# coding=utf-8
from __future__ import print_function, absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 Gina Häußge - Released under terms of the AGPLv3 License"

import dateutil.parser, dateutil.tz
import datetime
import requests
import sys

import logging
logging.basicConfig(format="%(asctime)-15s %(message)s")
logger = logging.getLogger(__name__)


# Github API URLs
USER_URL = "https://api.github.com/user"
ISSUES_URL = "https://api.github.com/repos/{repo}/issues?state=open"
ISSUES_SINCE_URL = "https://api.github.com/repos/{repo}/issues?state=open&since={since}"


def setup_logging(debug=False):
	root = logging.getLogger()

	# set proper level
	root.setLevel(logging.DEBUG if debug else logging.INFO)

	# we only want a stdout handler
	for handler in root.handlers:
		root.removeHandler(handler)
	console = logging.StreamHandler(stream=sys.stdout)
	console.setFormatter(logging.Formatter(fmt="%(asctime)-15s %(message)s"))
	root.addHandler(console)

	logging.getLogger("requests").setLevel(logging.WARN)


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
		"author_id": issue["user"]["id"],
		"body": issue["body"],
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

	logger.debug("Retrieving bot id from URL %s" % USER_URL)
	r = requests.get(USER_URL, headers=headers)
	myself = r.json()
	return myself["id"]


def no_pullrequests(issue):
	"""
	Filters the given issue, returns True iff issue is not a pull request

	:param issue: the issue to filter
	:return: true if issue matches the filter (see above), false otherwise
	"""

	return not "pull_request" in issue


def get_issues(token, repo, since=None, issue_filter=None, converter=None):
	"""
	Retrieves all issues for the ``repo``, optionally filtering them by
	``issue_filter`` (defaults to no filter if not set) and converting
	them via ``converter`` (defaults to no converter if not
	set).

	:param token:        token to use
	:param repo:         repository for which to retrieve the issues
	:param issue_filter: filter to apply, defaults to no filter
	:param converter:    converter to apply, defaults to no conversion
	:return: all issues not filtered out, converted via the converter
	"""

	headers = {"Authorization": "token {token}".format(token=token)}

	if issue_filter is None:
		issue_filter = lambda x: True
	if converter is None:
		converter = lambda x: x

	if since is None:
		url = ISSUES_URL
		since = ""
	else:
		url = ISSUES_SINCE_URL

	url = url.format(repo=repo, since=since)
	raw_issues = []
	while True:
		logger.debug("Retrieving issues from url %s" % url)
		r = requests.get(url, headers=headers)

		retrieved_issues = r.json()
		logger.debug("+ %d issues" % len(retrieved_issues))
		raw_issues += retrieved_issues

		if r.links and "next" in r.links and "url" in r.links["next"]:
			url = r.links["next"]["url"]
		else:
			break

	logger.debug("Found %d unfiltered issues" % len(raw_issues))
	issues = filter(issue_filter, raw_issues)
	logger.debug("%d issues left after filter" % len(issues))

	return map(converter, issues)


def load_config(file):
	"""
	Loads a config from the file

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

		logger.info("Saved current date and time for next run")


def print_version():
	from gitissuebot import _version
	print(_version.get_versions()["version"])
	sys.exit(0)
