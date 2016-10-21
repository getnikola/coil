Coil From Snaps
===============

Using
-----

This is going to change, currently it's a bit more manual than expected. First, installation
and setup::

    apt-get install redis-server # or equivalent
    snap install nikola
    snap install coil
    snap connect nikola:home core:home
    snap connect coil:network core:network
    snap connect coil:network-bind core:network-bind
    coil write_users

Then, configure your Nikola site as described in `the Coil docs <https://coil.readthedocs.io/admin/setup/#configuring-full-mode>`__ for "Full Mode".

Finally: run the different parts::

    cd /your/nikola/site
    # RQ workers
    coil.rqworker coil &

    # Gunicorn
    coil.gunicorn -b 127.0.0.1:8001 coil.web:app &

That will make your coil site available in http://127.0.0.1:8001 On first connection you will
change the admin credentials.and then you should proxy that via nginx or something.

Packaging
---------

::

   sh build.sh

Hey, it's easy ;-)

TODO
----

* Proper daemonization of coil.rqworker and coil.gunicorn
* Make write_users interactive and give it proper creds from the beginning
