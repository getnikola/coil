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

from __future__ import print_function, unicode_literals
from comet.utils import PERMISSIONS, parse_redis
import redis

__all__ = ['init', 'write_users']


def init():
    print("ERROR: Not implemented.")
    return 255


def write_users(dburl):
    data = {
        'username': 'admin',
        'realname': 'Website Administrator',
        'password':
            '$2a$12$.qMCcA2uOo0BKkDtEF/bueYtHjcdPBmfEdpxtktRwRTgsR7ZVTWmW',
    }

    for p in PERMISSIONS:
        data[p] = '1'

    db = redis.StrictRedis(**parse_redis(dburl))
    db.hmset('user:1', data)
    db.hset('users', 'admin', '1')
    if not db.exists('last_uid'):
        db.incr('last_uid')

    print("Username: admin")
    print("Password: admin")
    return 0
