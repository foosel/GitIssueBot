# coding=utf-8
from __future__ import print_function, absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 Gina Häußge - Released under terms of the AGPLv3 License"

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions

from .approve import argparser as approve_argparser, main as approve_main
from .autolabel import argparser as autolabel_argparser, main as autolabel_main

def main():
	import argparse

	parser = argparse.ArgumentParser(prog="gitissuebot")
	parser.add_argument("-v", "--version", action="version", version=__version__,
	                    help="Print the version and exit")

	subparsers = parser.add_subparsers()

	approve_parser = subparsers.add_parser("approve")
	approve_argparser(approve_parser)
	approve_parser.set_defaults(func=approve_main)

	autolabel_parser = subparsers.add_parser("autolabel")
	autolabel_argparser(autolabel_parser)
	autolabel_parser.set_defaults(func=autolabel_main)

	args = parser.parse_args()

	args.func(args)

if __name__ == "__main__":
	main()