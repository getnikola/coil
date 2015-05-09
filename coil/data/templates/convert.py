#!/usr/bin/env python
import io
import os
import sys
sys.path.append('/home/kwpolska/git/nikola/scripts')
import jinjify  # NOQA

files = os.listdir('mako/')
for i in files:
    with io.open('mako/' + i, 'r', encoding='utf-8') as fh:
        f = fh.readlines()
    o = jinjify.mako2jinja(f)
    with io.open('jinja/' + i, 'w', encoding='utf-8') as fh:
        fh.writelines(o)
