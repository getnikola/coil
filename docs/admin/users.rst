=====
Users
=====

.. index:: users

.. contents::

Users of Coil are stored in the Redis database.

Information stored
==================

The following data about users is stored:

Profile
-------

============  ==============  =======================================
Name          In Account      Notes
============  ==============  =======================================
``username``  Username        Used to log in
``realname``  Real name       Prominently displayed on posts
``email``     E-mail address  Used by administrators to contact users
``password``  Password        Hashed and salted using bcrypt
============  ==============  =======================================

Preferences
-----------

==================  =======================================  ==============
Name                In Account                               In Permissions
==================  =======================================  ==============
``want_all_posts``  Show me posts of other users by default  Want all posts
==================  =======================================  ==============

Permissions
-----------

Coil uses a very granular permission system.  Each user can have a different
set of permissions, depending on the needs of the organization.

================================  =============================  ===================
Name                              In Account                     In Permissions
================================  =============================  ===================
``active``                        n/a                            Active
``is_admin``                      User is an administrator       Admin
``can_edit_all_posts``            Can edit posts of other users  Can all posts
``can_upload_attachments``        Can upload attachments         Attachments
``can_rebuild_site``              Can rebuild the site           Rebuild
``can_transfer_post_authorship``  Can transfer post authorship   Transfer authorship
================================  =============================  ===================

Managing users and permissions
==============================

All administrators (people with the ``is_admin`` permission) get access to user
management views, accessible from the user menu.  They are:

Manage users
------------

This is a table of all users.  You can add new users at the bottom by typing in
a name and clicking *Create*.  You can also *Edit*, *Delete* or *Undelete*.

Deleting and undeleting users
`````````````````````````````

Even when you press the *Delete* button, the user stays in the database.  You can then *Undelete* them if you change your mind.

You could delete the user straight from Redis, but this is **not recommended** and
can have unexpected side effects.

Permissions
-----------

This is a table of all permissions in the system.  It can be used to quickly
modify the permission list for groups of users.  The teal buttons can be used
to select the permission for all users.
