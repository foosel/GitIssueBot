# coding=utf-8
#!/usr/bin/env python

import versioneer
versioneer.VCS = 'git'
versioneer.versionfile_source = 'src/gitissuebot/_version.py'
versioneer.versionfile_build = 'gitissuebot/_version.py'
versioneer.tag_prefix = ''
versioneer.parentdir_prefix = ''

from setuptools import setup, find_packages, Command
import os
import shutil
import glob


def package_data_dirs(source, sub_folders):
	dirs = []

	for d in sub_folders:
		for dirname, _, files in os.walk(os.path.join(source, d)):
			dirname = os.path.relpath(dirname, source)
			for f in files:
				dirs.append(os.path.join(dirname, f))

	return dirs


class CleanCommand(Command):
	description = "clean build artifacts"
	user_options = []
	boolean_options = []

	def initialize_options(self):
		pass

	def finalize_options(self):
		pass

	def run(self):
		if os.path.exists('build'):
			print "Deleting build directory"
			shutil.rmtree('build')
		eggs = glob.glob('GitIssueBot*.egg-info')
		for egg in eggs:
			print "Deleting %s directory" % egg
			shutil.rmtree(egg)


def get_cmdclass():
	cmdclass = versioneer.get_cmdclass()
	cmdclass.update({
		'clean': CleanCommand
	})
	return cmdclass


def params():
	name = "GitIssueBot"
	version = versioneer.get_version()
	cmdclass = get_cmdclass()

	description = "A bot for managing Github issues"
	long_description = open("README.md").read()
	classifiers = [
		"Development Status :: 3 - Alpha",
		"Environment :: Console",
		"Intended Audience :: Developers",
		"Intended Audience :: System Administrators",
		"License :: OSI Approved :: GNU Affero General Public License v3",
		"Topic :: Software Development :: Bug Tracking",
		"Topic :: Utilities"
	]
	author = "Gina Häußge"
	author_email = "osd@foosel.net"
	url = "http://www.github.com/foosel/GitIssueBot"
	license = "AGPLv3"

	packages = find_packages(where="src")
	package_dir = {"gitissuebot": "src/gitissuebot"}

	include_package_data = True
	zip_safe = False
	install_requires = open("requirements.txt").read().split("\n")

	entry_points = {
		"console_scripts": [
			"gitissuebot-approve = gitissuebot.approve:main"
		]
	}

	return locals()

setup(**params())
