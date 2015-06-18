=====================
Appendix A. Changelog
=====================

:Version: 1.3.1

v1.3.0
------

* Python 3 support

v1.2.2
------

* Don’t repeat Nikola dependencies to decrease maintenance burden

v1.2.1
------

* Specify deps in ``setup.py``

v1.2.0
------

* Added support for a Limited mode, which does not require Redis and rq
* Nikola v7.4.0 compatibility

v1.1.0
------

* Changed hashing mechanism to sha256 + bcrypt.
  Hashes will be fixed automatically on first login of each user.
* Added ``passlib`` dependency.
* rqworker queue is now named ``coil`` (was ``default``)
* add trailing slashes to all URLs
* use ``url_for()``
* add ``/rebuild/force/`` (== ``nikola build -a``)

v1.0.0
------

* RENAME TO *Coil CMS*
* User documentation
* Form validation
* Redis for storing data
* Rebuilding the site, using RQ as a task queue

v0.6.0
------

* Permission management
* ``setup.py`` and Python packaging
* ``comet`` management command
* more modern pages
* multiple issues fixed

v0.5.0
------

* Switch to Flask
* Cookie-based authentication
* User management
* Style wysihtml properly
* Rename to *Comet CMS*

v0.0.1
------

* Initial version
* Called ``nikola webapp``
* using bottle
* HTTP Basic “Authentication” (sorry)
* wysihtml
