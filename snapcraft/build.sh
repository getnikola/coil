#!/bin/sh
rm -rf parts/ stage/ prime/
snapcraft pull
# Pillow is not building properly
pip wheel --wheel-dir parts/coil/packages --disable-pip-version-check --no-index --find-links parts/coil/packages pillow
snapcraft prime
# Gunicorn has a silly chown which is blocked by sandboxing
sed -i /chown/d prime/lib/python2.7/site-packages/gunicorn/workers/base.py
snapcraft snap
