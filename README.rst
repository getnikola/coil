Comet CMS/Nikola WebApp
=======================

The goal of the ``comet_cms`` project is to make Nikola accessible for non-programmers, casual users, and all other people that don’t feel comfortable using the command line.

Setup
-----

1. Install Nikola from git.
2. ``pip install -r requirements.txt``
3. Add to your CSS on the Nikola side:
   <https://github.com/Voog/wysihtml/blob/master/examples/css/stylesheet.css>
4. Run ``nikola build``

Setup for the test repo (this one)::

    virtualenv comet_env
    cd comet
    source bin/activate
    git clone https://github.com/getnikola/nikola.git
    cd nikola
    pip install -e '.[extras]'
    cd ..
    git clone https://github.com/getnikola/comet_cms.git
    cd comet_cms
    pip install -r requirements.txt
    nikola build

Usage
-----

Run with ``python -m COMET``.

Default credentials: admin / admin.
