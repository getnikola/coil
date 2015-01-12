# -*- coding: utf-8 -*-

# Comet CMS v0.6.0
# Copyright © 2014-2015 Chris Warrick, Roberto Alsina, Henry Hirsch et al.

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
import kombu
import sys


__all__ = ['PERMISSIONS', 'USER_FIELDS', 'USER_ALL', 'parse_redis', 'ask',
           'ask_yesno']

USER_FIELDS = ['username', 'realname', 'password', 'email']
PERMISSIONS = ['active', 'is_admin', 'can_edit_all_posts', 'wants_all_posts',
               'can_upload_attachments', 'can_rebuild_site',
               'can_transfer_post_authorship']
USER_ALL = USER_FIELDS + PERMISSIONS


def parse_redis(url):
    """Parse Redis URL.

    :param str url: Redis URL
    :return: data for connection
    :rtype: dict
    :raises ValueError: invalid URL
    """
    redis_raw = kombu.parse_url(url)
    if redis_raw['transport'] == 'redis':
        return {'host': redis_raw['hostname'] or 'localhost',
                'port': redis_raw['port'] or 6379,
                'db': int(redis_raw['virtual_host'] or 0),
                'password': redis_raw['password']}
    elif redis_raw['transport'] == 'redis+socket':
        return {'unix_socket_path`': redis_raw['virtual_host']}
    else:
        raise ValueError("invalid Redis URL")


# The following two functions come from Nikola.
def ask(query, default=None):
    """Ask a question."""
    if default:
        default_q = ' [{0}]'.format(default)
    else:
        default_q = ''
    if sys.version_info[0] == 3:
        inp = raw_input("{query}{default_q}: ".format(
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
