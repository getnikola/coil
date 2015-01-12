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


u"""Comet CMS v{0}

Usage:
  comet devserver [-b | --browser] [-p <port> | --port=<port>]
  comet init [directory]
  comet write_users
  comet -h | --help
  comet --version

Options:
 -h, --help                Show help screen.
 --version                 Show version.
 -b, --browser             Open Comet in the browser after starting.
 -p <port>, --port=<port>  Port to use [default: 8001].
"""

import comet
import comet.utils
import sys
import docopt
import webbrowser

__doc__ = __doc__.format(comet.__version__)


def main():
    u"""The main function."""
    arguments = docopt.docopt(__doc__, version=u'Comet CMS v{0}'.format(
        comet.__version__))
    if arguments[u'init']:
        sys.exit(init(arguments))
    elif arguments[u'write_users']:
        sys.exit(write_users(arguments))
    elif arguments[u'devserver']:
        sys.exit(devserver(arguments))


def init(arguments):
    import comet.init
    return comet.init.init()


def write_users(arguments):
    import comet.init
    u = comet.utils.ask("Redis URL", "redis://")
    return comet.init.write_users(u)


def devserver(arguments):
    import comet.web
    if comet.web.app:
        port = int(arguments['--port'])
        url = 'http://localhost:{0}/'.format(port)
        comet.web.configure_url(url)
        comet.web.app.config['DEBUG'] = True

        if arguments['--browser']:
            webbrowser.open(url)

        comet.web.app.logger.info(u"Comet CMS running @ {0}".format(url))
        comet.web.app.run('localhost', port, debug=True)
        return 0
    else:
        print("FATAL: no conf.py found")
        return 255

if __name__ == '__main__':
    main()
