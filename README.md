![Maintenance](https://img.shields.io/maintenance/no/2021)

> ### Unmaintained as of 2021
>
> I no longer need GitIssueBot since I replaced its functionality with [some GitHub actions](https://github.com/OctoPrint/actions). 
> Repository preserved for historic reasons.

GitIssueBot
-----------

A bot for managing Github issues. Currently only supports approving and autolabeling newly created issues, more ideas
in the works.

## Approve

``gitissuebot approve`` allows to check any newly added or updated issues on the GitHub issue tracker whether the author included
a customizable phrase to be found in the contribution guidelines to check whether the user has read those guidelines.
The phrase may be included either in the body of the ticket or -- if it's not there -- be included as part of a comment
by the issue's **original author** to the issue. 

Issues not containing the phrase (checks are case-insensitive) will receive a configurable comment by the bot directing
the user to (re-)read the guidelines and the issue will be marked by a configurable label. Issues updated by their
author to include the phrase thereafter will be de-labeled again by the bot. If the issue is still lacking the phrase 
after a configurable grace period, the bot will automatically close the issue.

It's possible to configure phrases to be contained in the title of a newly created issue to make the bot ignore the
issue (e.g. you can instruct your users to prefix feature requests with "[Request]" and add that as an ignored title,
so that feature requests won't be processed by the bot). It's also possible to configure labels to ignore by the bot 
too.

### Configuration

Configuration of the bot can be done either completely via the command line (see `gitissue approve --help` for a list
of available arguments) or by supplying a configuration file via the `--config` command line argument from which to 
take the configuration.

An example for such a configuration file can be found below:

``` yaml
# The Github access token to use for accessing the Github API
# => https://help.github.com/articles/creating-an-access-token-for-command-line-use
token: someVeryLongToken

# The repository on which to work, in the format <username>/<repositoryname>
repo: myuser/myrepository

# Any issues added since that date will be processed
since: 2014-07-27 12:00:00+00:00

# Phrase to search for
phrase: I love cookies

# Label to add to issue if it's invalid
label: incomplete issue

# Grace period after which to close issues that are still invalid
grace_period: 14

# If set to true, invalid tickets will be closed directly instead of being marked
close_directly: false

# Labels if issues to ignore
ignored_labels:
- request
- support
- question
- misc
- accepted

# Parts of titles of issues to ignore
ignored_titles:
- '[Request]'
- '[Support]'
- '[Question]'
- '[Misc]'

# Reminder to add to incomplete issues
reminder: 'Hi @{author},


  It looks like there is some information missing from your ticket that will be needed
  in order to diagnose and fix the problem at hand. Please take a look at the [Contribution
  Guidelines](https://github.com/myuser/myrepository/blob/master/CONTRIBUTING.md), which 
  will tell you **exactly** what your ticket has to contain in order to be processable.


  I''m marking this one now as needing some more information. Please understand that
  if you do not provide that information within the next two weeks (until {until})
  I''ll close this ticket so it doesn''t clutter the bug tracker.


  Best regards,

  ~ Your friendly GitIssueBot


  PS: I''m just an automated script, not a human being.

  '

# Comment to add when closing an issue
closing: 'Since apparently some of the required information is still missing, I''m
  closing this now, sorry. Feel free to reopen this or create a new issue once you
  can provide **all** required information.

  '

# Comment to add when closing an issue directly
closingnow: 'Hi @{author},


  It looks like there is some information missing from your ticket that will be needed
  in order to diagnose and fix the problem at hand. Please take a look at the [Contribution
  Guidelines](https://github.com/myuser/myrepository/blob/master/CONTRIBUTING.md), which
  will tell you **exactly** what your ticket has to contain in order to be processable.


  I''m marking this one now as needing some more information. Please understand that
  if you do not provide that information within the next two weeks (until {until})
  I''ll close this ticket so it doesn''t clutter the bug tracker.


  Best regards,

  ~ Your friendly GitIssueBot


  PS: I''m just an automated script, not a human being.

  '

# Whether to only perform a dry run, without any writing requests against the API
dryrun: false

# Whether to enable debug logging
debug: false
```

The [generated token](https://help.github.com/articles/creating-an-access-token-for-command-line-use) needs to grant 
access to repo and -- if the issue of a private repository are to be managed -- also access to private repos.

### Usage

You will need to regularly execute the approve script, I recommend creating a cronjob for that and then let it do
its job daily or weekly or something like that.

## Autolabel

``gitissuebot autolabel`` allows to check any newly added or updated issues on the GitHub issue tracker for certain
tags in the title and apply labels based on the presence of these tags, thus allowing users to categorize their
issues themselves (by including the tag in the title), which otherwise is only possible for registered contributors
on Github.

### Configuration

Configuration of the bot can be done either completely via the command line (see `gitissue autolabel --help` for a list
of available arguments) or by supplying a configuration file via the `--config` command line argument from which to
take the configuration.

An example for such a configuration file can be found below:

``` yaml
# The Github access token to use for accessing the Github API
# => https://help.github.com/articles/creating-an-access-token-for-command-line-use
token: someVeryLongToken

# The repository on which to work, in the format <username>/<repositoryname>
repo: myuser/myrepository

# Any issues added since that date will be processed
since: 2014-07-27 12:00:00+00:00

# Mappings of title snippets to labels to be applied
mappings:
- tag: '[Request]'
  label: request
- tag: '[Support]'
  label: support
- tag: '[Question]'
  label: question
- tag: '[Misc]'
  label: misc

# Whether to search for the title snippets in a case insensitive manner
ignore_case: false

# Whether to only perform a dry run, without any writing requests against the API
dryrun: false

# Whether to enable debug logging
debug: false
```

The [generated token](https://help.github.com/articles/creating-an-access-token-for-command-line-use) needs to grant
access to repo and -- if the issue of a private repository are to be managed -- also access to private repos.

### Usage

You will need to regularly execute the autolabel script, I recommend creating a cronjob for that and then let it do
its job daily or weekly or something like that.

## PR Check

``gitissuebot prcheck`` allows checking any new pull requests to make sure they:

  * don't have an empty description,
  * have a title that matches some regex,
  * target only a `base` matching a whitelist and/or don't target a `base` matching a blacklist,
  * are only from a `head` matching a whitelist and/or aren't from a `head` matching a blacklist

This is to remind contributors of rules like "Create all PRs against branch X" or "always create a custom branch
for your PR".

### Configuration

``` yaml
# The Github access token to use for accessing the Github API
# => https://help.github.com/articles/creating-an-access-token-for-command-line-use
token: someVeryLongToken

# The repository on which to work, in the format <username>/<repositoryname>
repo: myuser/myrepository

# Any PRs created since that date will be processed
since: 2016-02-12 12:00:00+00:00

# allowed names for source branch names, won't be tested if unset
sources:
- some_patch

# blacklisted values for source branch names, won't be tested if unset
blacklisted_sources:
- master
- devel

# allowed values for target branch names, won't be tested if unset
targets:
- devel

# blacklisted values for target branch names, won't be tested if unset
blacklisted_targets:
- master

# Text of reminder comment to post to PRs for which problems are detected.
# 
# The following placeholder are possible:
# - author: the name of the author of the PR
# - source_repo: repository of the PR head/source
# - source_branch: branch name of the PR head/source
# - target_repo: repository of the PR base/target
# - target_branch: branch name of the PR base/target
# - problems: newline separated list of problem strings for detected problems,
#   strings are defined below
reminder: 'Hi @{author},


  Thank you for your contribution! Sadly it looks like there is something wrong with
  this PR from branch `{source_branch}` on repository `{source_repo}` to branch `{target_branch}`
  on repository `{target_repo}`:


  {problems}


  Please take a look at the [section on PRs in the Contribution Guidelines](https://github.com/myuser/myrepository/blob/master/CONTRIBUTING.md)
  and make sure that your PR follows them. Thank you!


  Best regards,

  ~ Your friendly GitIssueBot


  PS: I''m just an automated script, not a human being.

  '

# Label to apply to PRs with problems - PRs with that label won't be processed by prcheck again
label: needs some work

# Strings to write into the comment for detected problems
problems:

  # source branch was not among whitelisted names
  invalid_source: '  * Your PR''s source branch `{source_branch}` isn''t among the
    allowed source branches: {sources}'

  # source branch was among blacklisted names
  blacklisted_source: '  * Your PR''s source branch `{source_branch}` is among the
    blacklisted source branches: {blacklisted_sources}'

  # target branch was not among whitelisted names
  invalid_target: '  * Your PR''s target branch `{target_branch}` isn''t among the
    allowed target branches: {targets}'

  # target branch was among blacklisted names
  blacklisted_target: '  * Your PR''s target branch `{target_branch}` is among the
    blacklisted target branches: {blacklisted_targets}'

  # PR title is invalid
  invalid_title: '  * Your PR does has an invalid title. Please update it to start
    with one of [bugfix], [feature], [critical], [new locale], [misc], [tests], or
    [pkg].'

  # PR description was empty
  empty_body: '  * Your PR does have an empty description. Please explain what your
    PR does, how you''ve tested it, etc.'

# Regex for title
title_regex: '\[bugfix\] |\[feature\] |\[critical\] |\[new locale\] |\[misc\] |\[tests\]
  |\[pkg\] '

# Whether to match branch names in a case insensitive manner
ignore_case: false

# Whether to only perform a dry run, without any writing requests against the API
dryrun: false

# Whether to enable debug logging
debug: false
```

The [generated token](https://help.github.com/articles/creating-an-access-token-for-command-line-use) needs to grant
access to repo and -- if the issue of a private repository are to be managed -- also access to private repos.

### Usage

You will need to regularly execute the autolabel script, I recommend creating a cronjob for that and then let it do
its job daily or weekly or something like that.

## Contributors

- [Philippe Neumann](https://github.com/demod) (brain storming, sanity check of the concept)
