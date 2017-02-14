=====================
Appendix A. Changelog
=====================

:Version: 1.3.10

1.3.10
    * Add `coil unlock` command
    * Fix links to docs

1.3.9
    * Work on non-English sites (fix #45)

1.3.8
    * Clean up requirements (issue #40)

1.3.7
    * Nikola v7.6.4 compatibility

1.3.6
    * Patch URLs for HTTPS sites
    * Really add descriptions for icons (got lost between branches)

1.3.5
    * Add icon descriptions for the navigation bar

1.3.4
    * Link to demo site in documentation
    * Support reCAPTCHA for logins (for demo site)
    * Support preventing some users from editing the site (for demo site)

1.3.3
    Remove yesterday’s new options.  Please do not use v1.3.2.

1.3.2
    * Added two options that should not be used, EVER. Please ignore them.

1.3.1
    * Use rq from PyPI instead of GitHub

1.3.0
    * Python 3 support

1.2.2
    * Don’t repeat Nikola dependencies to decrease maintenance burden

1.2.1
    * Specify deps in ``setup.py``

1.2.0
    * Added support for a Limited mode, which does not require Redis and rq
    * Nikola v7.4.0 compatibility

1.1.0
    * Changed hashing mechanism to sha256 + bcrypt.
      Hashes will be fixed automatically on first login of each user.
    * Added ``passlib`` dependency.
    * rqworker queue is now named ``coil`` (was ``default``)
    * add trailing slashes to all URLs
    * use ``url_for()``
    * add ``/rebuild/force/`` (== ``nikola build -a``)

1.0.0
    * RENAME TO *Coil CMS*
    * User documentation
    * Form validation
    * Redis for storing data
    * Rebuilding the site, using RQ as a task queue

0.6.0
    * Permission management
    * ``setup.py`` and Python packaging
    * ``comet`` management command
    * more modern pages
    * multiple issues fixed

0.5.0
    * Switch to Flask
    * Cookie-based authentication
    * User management
    * Style wysihtml properly
    * Rename to *Comet CMS*

0.0.1
    * Initial version
    * Called ``nikola webapp``
    * using bottle
    * HTTP Basic “Authentication” (sorry)
    * wysihtml
