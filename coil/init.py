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

from __future__ import print_function, unicode_literals
from coil.utils import PERMISSIONS
import redis

__all__ = ['init', 'write_users']


def init():
    """Initialize a site."""
    print("Please read the documentation and set up Coil CMS manually:")
    print("https://coil.readthedocs.io/admin/setup/")
    return 255


def write_users(dburl):
    """Write users to the DB."""
    data = {
        'username': 'admin',
        'realname': 'Website Administrator',
        'email': 'coil@example.com',
        'password':
            r'$bcrypt-sha256$2a,12$NNtd2TC9mZO6.EvLwEwlLO$axojD34/iE8x'
            r'QitQnCCOGPhofgmjNdq',
    }

    for p in PERMISSIONS:
        data[p] = '1'

    db = redis.StrictRedis.from_url(dburl)
    db.hmset('user:1', data)
    db.hset('users', 'admin', '1')
    if not db.exists('last_uid'):
        db.incr('last_uid')

    print("Username: admin")
    print("Password: admin")
    return 0
