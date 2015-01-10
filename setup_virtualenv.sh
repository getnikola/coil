#!/bin/bash
virtualenv comet_env
cd comet_env
source bin/activate
git clone https://github.com/getnikola/nikola.git
cd nikola
pip install -e '.[extras]'
cd ..
git clone https://github.com/getnikola/comet_cms.git
cd comet_cms
pip install -e .
cd SITE
nikola build
