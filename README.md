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

The [generated token](https://help.github.com/articles/creating-an-access-token-for-command-line-use) needs to grant
access to repo and -- if the issue of a private repository are to be managed -- also access to private repos.

### Usage

You will need to regularly execute the autolabel script, I recommend creating a cronjob for that and then let it do
its job daily or weekly or something like that.

## Contributors

- [Philippe Neumann](https://github.com/demod) (brain storming, sanity check of the concept)
