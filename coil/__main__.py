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


u"""Coil CMS v{0}

Usage:
  coil devserver [-b | --browser] [-p <port> | --port=<port>] [--no-url-fix] [--no-debug]
  coil unlock
  coil write_users
  coil -h | --help
  coil --version

Options:
 -h, --help                Show help screen.
 --version                 Show version.
 -b, --browser             Open Coil CMS in the browser after starting.
 -p <port>, --port=<port>  Port to use [default: 8001].
"""

from __future__ import unicode_literals

import coil
import coil.utils
import sys
import docopt
import webbrowser

__doc__ = __doc__.format(coil.__version__)


def main():
    """The main function."""
    arguments = docopt.docopt(__doc__, version='Coil CMS v{0}'.format(
        coil.__version__))
    if arguments['write_users']:
        sys.exit(write_users(arguments))
    elif arguments['devserver']:
        sys.exit(devserver(arguments))
    elif arguments['unlock']:
        sys.exit(unlock(arguments))


def init(arguments):
    """Run coil init."""
    import coil.init
    return coil.init.init()


def write_users(arguments):
    """Write users to the DB."""
    import coil.init
    u = coil.utils.ask("Redis URL", "redis://localhost:6379/0")
    return coil.init.write_users(u)


def devserver(arguments):
    """Run a development server."""
    import coil.web
    if coil.web.app:
        port = int(arguments['--port'])
        url = 'http://localhost:{0}/'.format(port)
        coil.web.configure_url(url)
        coil.web.app.config['DEBUG'] = True

        if arguments['--browser']:
            webbrowser.open(url)

        coil.web.app.logger.info("Coil CMS running @ {0}".format(url))
        coil.web.app.run('localhost', port, debug=True)
        return 0
    else:
        print("FATAL: no conf.py found")
        return 255


def unlock(arguments):
    """Unlock the database."""
    import redis
    u = coil.utils.ask("Redis URL", "redis://localhost:6379/0")
    db = redis.StrictRedis.from_url(u)
    db.set('site:lock', 0)
    print("Database unlocked.")
    return 0

if __name__ == '__main__':
    main()
