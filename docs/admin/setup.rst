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

As such, you must configure Nikola first before you start Coil.

Virtualenv
==========

Create a virtualenv in ``/var/coil`` and install Coil in it.

.. code-block:: console

    # virtualenv-2.7 /var/coil
    # cd /var/coil
    # source bin/activate
    # pip install coil uwsgi

Redis
=====

You need to set up a `Redis <http://redis.io/>`_ server.  Make sure it starts
at boot.

RQ
==

You need to set up a `RQ <http://python-rq.org>`_ worker.  Make sure it starts
at boot, after Redis.  Here is a sample ``.service`` file for systemd:

.. code-block:: ini

    [Unit]
    Description=RQWorker Service
    After=redis.service

    [Service]
    Type=simple
    ExecStart=/var/coil/bin/rqworker
    User=nobody
    Group=nobody

    [Install]
    WantedBy=multi-user.target


Nikola and ``conf.py``
======================

Start by setting up Nikola.  This can be done using ``nikola init``.

.. code-block:: console

    # mkdir /var/coil
    # cd /var/coil
    # nikola init my_coil_site
    Creating Nikola Site
    ====================

    [a wizard will guide you through configuration]

    [2015-01-10T18:16:35Z] INFO: init: Created empty site at my_coil_site.
    # cd my_coil_site

Then, you must make some changes to the config:

 * ``coil_SECRET_KEY`` — a bunch of random characters, needed for sessions.
   **Store it in a safe place** — git is not one!  You can use
   ``os.urandom(24)`` to generate something good.
 * ``coil_URL`` — the URL under which Coil can be accessed.
 * ``REDIS_URL`` — the URL of your Redis database.
 * Modify ``POSTS`` and ``PAGES``, replacing ``.txt`` by ``.html``.

Redis URL syntax
----------------

* ``redis://[:password]@localhost:6379/0`` (TCP)
* ``rediss://[:password]@localhost:6379/0`` (TCP over SSL)
* ``unix://[:password]@/path/to/socket.sock?db=0`` (Unix socket)

The default URL is ``redis://localhost:6379/0``.

CSS for the site
----------------

Finally, you must add `some CSS`__ for wysihtml5.  The easiest way to do this
is by downloading the raw ``.css`` file as ``files/assets/css/custom.css``.

__ https://github.com/Voog/wysihtml/blob/master/examples/css/stylesheet.css

First build
===========

When you are done configuring nikola, run ``nikola build``.

.. code-block:: console

    # nikola build

Users
=====

Run ``coil write_users``:

.. code-block:: console

    # coil write_users
    Redis URL [redis://]:
    Username: admin
    Password: admin


You will be able to add more users and change the admin credentials (which you
should do!) later.  See also: :doc:`users`.

Permissions
===========

.. code-block:: console

    # chown -Rf nobody:nobody .

Chown ``my_coil_site`` *recursively* to ``nobody``, or whatever
user Coil will run as.  Coil must be able to write to this directory.

Make sure to fix permissions if you fool around the site directory!

Server
======

For testing purposes, you can use ``coil devserver``.  It should **NOT** be used
in production.  You should use uWSGI Emperor and nginx in a real environment.

uWSGI
-----

Sample uWSGI configuration:


.. code-block:: ini

    [uwsgi]
    emperor = true
    socket = 127.0.0.1:3031
    chdir = /var/coil/my_coil_site
    master = true
    threads = 5
    binary-path = /var/coil/bin/uwsgi
    virtualenv = /var/coil
    module = coil.web
    callable = app
    plugins = python2
    uid = nobody
    gid = nobody
    processes = 3
    logger = file:/var/coil/my_coil_site/uwsgi.log

.. note::

   ``python2`` may also be ``python`` this depending on your environment.

nginx
-----

Sample nginx configuration:

.. code-block:: nginx

    server {
        listen 80;
        server_name coil.example.com;
        root /var/coil/my_coil_site;

        location / {
            include uwsgi_params;
            uwsgi_pass 127.0.0.1:3031;
        }

        location /favicon.ico {
            alias /var/coil/my_coil_site/output/favicon.ico;
        }

        location /assets {
            alias /var/coil/my_coil_site/output/assets;
        }

        location /coil_assets {
            alias /var/coil/lib/python2.7/site-packages/coil/data/coil_assets;
        }

        location /bower_components {
            alias /var/coil/lib/python2.7/site-packages/coil/data/bower_components;
        }
    }

.. _Nikola: https://getnikola.com/
