# -*- coding: utf-8 -*-

# Coil CMS v1.2.0
# Copyright © 2014-2017 Chris Warrick, Roberto Alsina, Henry Hirsch et al.

# Permission is hereby granted, free of charge, to any
# person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the
# Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the
# Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice
# shall be included in all copies or substantial portions of
# the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY
# KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
# PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS
# OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import unicode_literals
from nikola.post import Post
import sys
import json
import time


__all__ = ['PERMISSIONS', 'USER_FIELDS', 'USER_ALL', 'ask', 'ask_yesno',
           'SiteProxy']

USER_FIELDS = ['username', 'realname', 'password', 'email']
# internal order
PERMISSIONS = ['active', 'is_admin', 'can_edit_all_posts', 'wants_all_posts',
               'can_upload_attachments', 'can_rebuild_site',
               'can_transfer_post_authorship', 'must_change_password']
# special display order
PERMISSIONS_E = ['active', 'is_admin', 'must_change_password',
                 'can_edit_all_posts', 'wants_all_posts',
                 'can_upload_attachments', 'can_rebuild_site',
                 'can_transfer_post_authorship']
USER_ALL = USER_FIELDS + PERMISSIONS


# The following two functions come from Nikola.
def ask(query, default=None):
    """Ask a question."""
    if default:
        default_q = ' [{0}]'.format(default)
    else:
        default_q = ''
    if sys.version_info[0] == 3:
        inp = input("{query}{default_q}: ".format(
            query=query, default_q=default_q)).strip()
    else:
        inp = raw_input("{query}{default_q}: ".format(
            query=query, default_q=default_q).encode('utf-8')).strip()
    if inp or default is None:
        return inp
    else:
        return default


def ask_yesno(query, default=None):
    """Ask a yes/no question."""
    if default is None:
        default_q = ' [y/n]'
    elif default is True:
        default_q = ' [Y/n]'
    elif default is False:
        default_q = ' [y/N]'
    if sys.version_info[0] == 3:
        inp = raw_input("{query}{default_q} ".format(
            query=query, default_q=default_q)).strip()
    else:
        inp = raw_input("{query}{default_q} ".format(
            query=query, default_q=default_q).encode('utf-8')).strip()
    if inp:
        return inp.lower().startswith('y')
    elif default is not None:
        return default
    else:
        # Loop if no answer and no default.
        return ask_yesno(query, default)


class SiteProxy(object):
    """A proxy for accessing the site in a multiprocessing-safe manner."""

    def __init__(self, db, site, logger):
        """Initialize a proxy."""
        self.db = db
        self._site = site
        self.config = site.config
        self.messages = site.MESSAGES
        self.logger = logger

        self.revision = ''
        self._timeline = []
        self._posts = []
        self._all_posts = []
        self._pages = []

        self.scan_posts()

    def reload_site(self):
        """Reload the site from the database."""
        rev = int(self.db.get('site:rev'))
        if rev != self.revision and self.db.exists('site:rev'):
            timeline = self.db.lrange('site:timeline', 0, -1)
            self._timeline = []
            for data in timeline:
                data = json.loads(data.decode('utf-8'))
                self._timeline.append(Post(data[0], self.config, data[1],
                                           data[2], data[3], self.messages,
                                           self._site.compilers[data[4]]))

            self._read_indexlist('posts')
            self._read_indexlist('all_posts')
            self._read_indexlist('pages')

            self.revision = rev
            self.logger.info("Site updated to revision {0}.".format(rev))
        elif rev == self.revision and self.db.exists('site:rev'):
            pass
        else:
            self.logger.warn("Site needs rescanning.")

    def _read_indexlist(self, name):
        """Read a list of indexes."""
        setattr(self, '_' + name, [self._timeline[int(i)] for i in
                                   self.db.lrange('site:{0}'.format(name), 0,
                                                  -1)])

    def _write_indexlist(self, name):
        """Write a list of indexes."""
        d = [self._site.timeline.index(p) for p in getattr(self._site, name)]
        self.db.delete('site:{0}'.format(name))
        if d:
            self.db.rpush('site:{0}'.format(name), *d)

    def scan_posts(self, really=True, ignore_quit=False, quiet=True):
        """Rescan the site."""
        while (self.db.exists('site:lock') and
               int(self.db.get('site:lock')) != 0):
            self.logger.info("Waiting for DB lock...")
            time.sleep(0.5)
        self.db.incr('site:lock')
        self.logger.info("Lock acquired.")
        self.logger.info("Scanning site...")

        self._site.scan_posts(really, ignore_quit, quiet)

        timeline = []
        for post in self._site.timeline:
            data = [post.source_path, post.folder, post.is_post,
                    post._template_name, post.compiler.name]
            timeline.append(json.dumps(data))
        self.db.delete('site:timeline')
        if timeline:
            self.db.rpush('site:timeline', *timeline)

        self._write_indexlist('posts')
        self._write_indexlist('all_posts')
        self._write_indexlist('pages')

        self.db.incr('site:rev')

        self.db.decr('site:lock')
        self.logger.info("Lock released.")
        self.logger.info("Site scanned.")
        self.reload_site()

    @property
    def timeline(self):
        """Get timeline, reloading the site if needed."""
        rev = int(self.db.get('site:rev'))
        if rev != self.revision:
            self.reload_site()

        return self._timeline

    @property
    def posts(self):
        """Get posts, reloading the site if needed."""
        rev = int(self.db.get('site:rev'))
        if rev != self.revision:
            self.reload_site()

        return self._posts

    @property
    def all_posts(self):
        """Get all_posts, reloading the site if needed."""
        rev = self.db.get('site:rev')
        if int(rev) != self.revision:
            self.reload_site()

        return self._all_posts

    @property
    def pages(self):
        """Get pages, reloading the site if needed."""
        rev = self.db.get('site:rev')
        if int(rev) != self.revision:
            self.reload_site()

        return self._pages
