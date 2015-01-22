=========
Internals
=========

.. index:: internals

Database schema
===============

User storage
------------

============  ======  ===============================================================================
Name          Type    Contents
============  ======  ===============================================================================
``users``     hash    Hash mapping usernames to UIDs
``user:uid``  hash    All the data we have on the user (see :doc:`Users documentation <admin/users>`)
============  ======  ===============================================================================

Caching site
------------

==================  ======  ============================================================================
Name                Type    Contents
==================  ======  ============================================================================
``site:timeline``   list    list of JSON lists of data needed to initialize a Post
``site:all_posts``  list    list of indexes for ``timeline`` matching ``all_posts``
``site:posts``      list    list of indexes for ``timeline`` matching ``posts``
``site:pages``      list    list of indexes for ``timeline`` matching ``pages``
``site:rev``        string  revision (incremented at each scan; used to determine if updates are needed)
``site:lock``       string  lock on site DB
==================  ======  ============================================================================

``coil.utils``
==============

.. index:: coil.utils
.. automodule:: coil.utils
   :members:

``coil.web``
============

.. index:: coil.web
.. automodule:: coil.web
   :members:
