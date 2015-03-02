# GitIssueBot Changelog

## 0.2.0 (2015-03-02)

### Features

* Old trigger phrases can now be tracked along side with the current one, causing the issue to be validated but a
  comment to be added to remind the user to review the adjusted contribution guidelines
* New command ``autolabel``: Allows definition of a set of title tags (e.g. "[Request]") for which to apply defined
  labels if found in an issue

### Improvements

* Also recognize changes in title tags and labels for validating a formerly invalidated issue

### Bug Fixes

* [#1](https://github.com/foosel/GitIssueBot/issues/1) - Pinned version numbers of dependencies to reduce risks of
  breaking API changes
* [#2](https://github.com/foosel/GitIssueBot/pull/2) - Explicitely using unicode for printing anything coming from the API
* Unreported:
  * Properly calculate, format and URL encode the ``since`` parameter for fetching issues
  * Iterate through ``links`` provided by Github API to retrieve all issues, not just the first page
  * Removed accidentally committed ``.pyc`` files

([Commits](https://github.com/foosel/GitIssueBot/compare/0.1.0...0.2.0))

## 0.1.0 (2014-07-27)

Initial release
