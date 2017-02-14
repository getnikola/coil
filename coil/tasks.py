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

import subprocess
import os
from rq import get_current_job
from sys import executable
from redis import StrictRedis


def build(dburl, sitedir, mode):
    """Build a site."""
    if mode == 'force':
        amode = ['-a']
    else:
        amode = []
    oldcwd = os.getcwd()
    os.chdir(sitedir)
    db = StrictRedis.from_url(dburl)
    job = get_current_job(db)
    job.meta.update({'out': '', 'milestone': 0, 'total': 1, 'return': None,
                     'status': None})
    job.save()
    p = subprocess.Popen([executable, '-m', 'nikola', 'build'] + amode,
                         stderr=subprocess.PIPE)

    milestones = {
        'done!': 0,
        'render_posts': 0,
        'render_pages': 0,
        'generate_rss': 0,
        'render_indexes': 0,
        'sitemap': 0
    }
    out = []

    while p.poll() is None:
        nl = p.stderr.readline().decode('utf-8')
        for k in milestones:
            if k in nl:
                milestones[k] = 1
        out.append(nl)
        job.meta.update({'milestone': sum(milestones.values()), 'total':
                         len(milestones), 'out': ''.join(out), 'return': None,
                         'status': None})
        job.save()

    out += p.stderr.readlines()

    out = ''.join(out)
    job.meta.update({'milestone': len(milestones), 'total': len(milestones),
                     'out': ''.join(out), 'return': p.returncode, 'status':
                     p.returncode == 0})
    job.save()
    os.chdir(oldcwd)
    return p.returncode


def orphans(dburl, sitedir):
    """Remove all orphans in the site."""
    oldcwd = os.getcwd()
    os.chdir(sitedir)
    db = StrictRedis.from_url(dburl)
    job = get_current_job(db)
    job.meta.update({'out': '', 'return': None, 'status': None})
    job.save()
    returncode, out = orphans_single(default_exec=True)

    job.meta.update({'out': out, 'return': returncode, 'status':
                     returncode == 0})
    job.save()
    os.chdir(oldcwd)
    return returncode


def build_single(mode):
    """Build, in the single-user mode."""
    if mode == 'force':
        amode = ['-a']
    else:
        amode = []
    if executable.endswith('uwsgi'):
        # hack, might fail in some environments!
        _executable = executable[:-5] + 'python'
    else:
        _executable = executable
    p = subprocess.Popen([_executable, '-m', 'nikola', 'build'] + amode,
                         stderr=subprocess.PIPE)
    p.wait()
    rl = p.stderr.readlines()
    try:
        out = ''.join(rl)
    except TypeError:
        out = ''.join(l.decode('utf-8') for l in rl)
    return (p.returncode == 0), out


def orphans_single(default_exec=False):
    """Remove all orphans in the site, in the single user-mode."""
    if not default_exec and executable.endswith('uwsgi'):
        # default_exec => rq => sys.executable is sane
        _executable = executable[:-5] + 'python'
    else:
        _executable = executable
    p = subprocess.Popen([_executable, '-m', 'nikola', 'orphans'],
                         stdout=subprocess.PIPE)
    p.wait()
    files = [l.strip().decode('utf-8') for l in p.stdout.readlines()]
    for f in files:
        if f:
            os.unlink(f)

    out = '\n'.join(files)
    return p.returncode, out
