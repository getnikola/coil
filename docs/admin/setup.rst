=====
Setup
=====

.. index:: setup

.. contents::

How Coil works alongside Nikola
===============================

Coil requires Nikola to work.  `Nikola`_ is a static site generator, written
in Python.  Coil manages the files that are then used by Nikola to build the
site.

As such, you must configure Nikola first before you start Coil.  You can also
use an existing site.

Virtualenv
==========

Create a virtualenv in ``/srv/coil`` and install Coil, Nikola, uWSGI and rq in it.

.. code-block:: console

    # virtualenv-2.7 /srv/coil
    # cd /srv/coil
    # source bin/activate
    # pip install nikola coil uwsgi
    # pip install 'git+https://github.com/nvie/rq.git#egg=rq'

Nikola and ``conf.py``
======================

Start by setting up Nikola.  This can be done using ``nikola init``.

.. code-block:: console

    # mkdir /srv/coil
    # cd /srv/coil
    # nikola init my_coil_site
    Creating Nikola Site
    ====================

    [a wizard will guide you through configuration]

    [2015-01-10T18:16:35Z] INFO: init: Created empty site at my_coil_site.
    # cd my_coil_site

Then, you must make some changes to the config:

 * ``COIL_SECRET_KEY`` — a bunch of random characters, needed for sessions.
   **Store it in a safe place** — git is not one!  You can use
   ``os.urandom(24)`` to generate something good.
 * ``COIL_URL`` — the URL under which Coil can be accessed.
 * ``_MAKO_DISABLE_CACHING = True``
 * Modify ``POSTS`` and ``PAGES``, replacing ``.txt`` with ``.html``.
 * You must set the mode (Limited vs Full) and configure it accordingly — see
   next section for details.

CSS for the site
----------------

You must add `some CSS`__ for wysihtml5.  The easiest way to do this
is by downloading the raw ``.css`` file and saving it as ``files/assets/css/custom.css``.

__ https://github.com/Voog/wysihtml/blob/master/examples/css/stylesheet.css

Special config for demo sites
-----------------------------

The `demo site <https://coildemo-admin.getnikola.com/>`_ uses the following two
settings, which might also be useful for some environments:

* ``COIL_LOGIN_CAPTCHA`` — if you want reCAPTCHA to appear on the login page
   (aimed at plugic environments, eg. the demo site), set this to a dict of
   ``{'enabled': True, 'site_key': '', 'secret_key': ''}`` and fill in your data.
   If you don’t want a CAPTCHA, don’t set this setting.
* ``COIL_USERS_PREVENT_EDITING`` — list of user IDs (integers) that cannot edit their
  profiles.

Limited Mode vs. Full Mode
==========================

Coil can run in two modes: Limited and Full.

**Limited Mode**:

* does not require a database, is easier to setup
* stores its user data in ``conf.py`` (no ability to modify users on-the-fly)
* MUST run as a single process (``processes=1`` in uWSGI config)

**Full Mode**:

* requires Redis and RQ installed and running
* stores its user data in the Redis database (you can modify users on-the-fly)
* may run as multiple processes

Configuring Limited Mode
------------------------

You need to add the following to your config file:

.. code:: python

    COIL_LIMITED = True
    COIL_USERS = {
        '1': {
            'username': 'admin',
            'realname': 'Website Administrator',
            'password': '$bcrypt-sha256$2a,12$St3N7xoStL7Doxpvz78Jve$3vKfveUNhMNhvaFEfJllWEarb5oNgNu',
            'must_change_password': False,
            'email': 'info@getnikola.com',
            'active': True,
            'is_admin': True,
            'can_edit_all_posts': True,
            'wants_all_posts': True,
            'can_upload_attachments': True,
            'can_rebuild_site': True,
            'can_transfer_post_authorship': True,
        },
    }

The default user is ``admin`` with the password ``admin``.  New users can be
created by creating a similar dict.  Password hashes can be calculated on the
*Account* page.  Note that you are responsible for changing user passwords
(users should provide you with hashes and you must add them manually and
restart Coil) — consider not setting ``must_change_password`` in Limited mode.

**Continue** with `First build`_.

Configuring Full Mode
---------------------

Full Mode requires much more extra configuration.

Redis
~~~~~

You need to set up a `Redis <http://redis.io/>`_ server.  Make sure it starts
at boot.

RQ
~~

You need to set up a `RQ <http://python-rq.org>`_ worker.  Make sure it starts
at boot, after Redis.  Here is a sample ``.service`` file for systemd:

.. code-block:: ini

    [Unit]
    Description=RQWorker Service
    After=redis.service

    [Service]
    Type=simple
    ExecStart=/srv/coil/bin/rqworker coil
    User=nobody
    Group=nobody

    [Install]
    WantedBy=multi-user.target

Users
~~~~~

Run ``coil write_users``:

.. code-block:: console

    # coil write_users
    Redis URL [redis://]:
    Username: admin
    Password: admin


You will be able to add more users and change the admin credentials (which you
should do!) later.  See also: :doc:`users`.

conf.py additions
~~~~~~~~~~~~~~~~~

You must add ``COIL_LIMITED = False`` and ``COIL_REDIS_URL``, which is an URL to
your Redis database.  The accepted formats are:

* ``redis://[:password]@localhost:6379/0`` (TCP)
* ``rediss://[:password]@localhost:6379/0`` (TCP over SSL)
* ``unix://[:password]@/path/to/socket.sock?db=0`` (Unix socket)

The default URL is ``redis://localhost:6379/0``.


First build
===========

When you are done configuring Nikola, Coil and any other dependencies, run
``nikola build``.  This will build an empty Nikola site that can now be hosted
outside.  You need to do this, because Coil itself uses some assets from this
site.

.. code-block:: console

    # nikola build

Permissions
===========

.. code-block:: console

    # chown -Rf nobody:nobody .

Chown ``my_coil_site`` *recursively* to ``nobody``, or whatever
user Coil will run as.  Coil must be able to write to this directory.

Make sure to fix permissions if you fool around the site directory!

Server
======

Built-in development server
---------------------------

For testing purposes, or for ad-hoc usage (especially in Limited mode), you can
just run ``coil devserver``.  However, it should **NOT** be used in production.
In a public environment, especially in Full mode, you should use uWSGI Emperor
and nginx instead.

If you are on Windows and the server crashes, try ``python -m coil devserver``.

uWSGI
-----

Sample uWSGI configuration:

.. note::

   ``python2`` may also be ``python``, depending on your environment.

.. warning::

   ``processes`` **MUST** be set to 1 if running in Limited Mode.

.. code-block:: ini

    [uwsgi]
    emperor = true
    socket = 127.0.0.1:3031
    chdir = /srv/coil/my_coil_site
    master = true
    threads = 5
    binary-path = /srv/coil/bin/uwsgi
    virtualenv = /srv/coil
    module = coil.web
    callable = app
    plugins = python2,logfile
    uid = nobody
    gid = nobody
    processes = 3
    logger = file:/srv/coil/my_coil_site/uwsgi.log

nginx
-----

Sample nginx configuration:

.. note::

   This configuration block assumes you followed the guide.  You may need to
   change the location aliases to match your system.

   You should change ``server_name`` to something you own and can run the
   server on.

.. code-block:: nginx

    server {
        listen 80;
        server_name coil.example.com;
        root /srv/coil/my_coil_site;

        location / {
            include uwsgi_params;
            uwsgi_pass 127.0.0.1:3031;
        }

        location /favicon.ico {
            alias /srv/coil/my_coil_site/output/favicon.ico;
        }

        location /assets {
            alias /srv/coil/my_coil_site/output/assets;
        }

        location /coil_assets {
            alias /srv/coil/lib/python2.7/site-packages/coil/data/coil_assets;
        }

        location /bower_components {
            alias /srv/coil/lib/python2.7/site-packages/coil/data/bower_components;
        }
    }

Other web servers
-----------------

You can also use any other web or WSGI server.  You must take care of:

* location aliases for ``/favicon.ico``, ``/assets``, ``/coil_assets``,
  ``/bower_components`` — see above for sample destinations
* correct process count (must be 1 in Limited mode)

.. _Nikola: https://getnikola.com/
