# -*- coding: utf-8 -*-

# Copyright © 2014 Roberto Alsina

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
import json
import os
import webbrowser
import io
import hashlib
import bottle as b

from nikola.plugin_categories import Command
_site = None
TITLE = 'webapp'
USERNAME = ''
REALNAME = ''
USERS = {}
auth_title = 'Comet CMS Login'

json_path = os.path.join(os.path.dirname(__file__), 'users.json')

def auth_check(user, passwd):
    global USERNAME, REALNAME, USERS
    passwd = passwd.encode('utf-8')
    passwd = passwd_hash(passwd)
    status = user in USERS and USERS[user]['password'] == passwd
    if status:
        USERNAME = user
        REALNAME = USERS[user]['name']
    return status

def init_site():
    _site.scan_posts(really=True)

def passwd_hash(passwd):
    # safer algorithm?
    return hashlib.sha512(passwd).hexdigest()

def read_users():
    global USERS
    with io.open(json_path, 'rb') as fh:
        USERS = json.load(fh)

def write_users():
    global USERS
    with io.open(json_path, 'wb') as fh:
        json.dump(USERS, fh, indent=4)

def generate_menu_alt():
    return  """<li><a href="/profile">{0} [{1}]</a></li>""".format(REALNAME, USERNAME)

read_users()

class Webapp(Command):

    name = "webapp"
    doc_usage = "[[-p] port_number] | [[-u] -b]"
    doc_purpose = "run CRUD interface for the site"
    cmd_options = [
        {
            'name': 'browser',
            'short': 'b',
            'type': bool,
            'help': 'Start a web browser.',
            'default': False,
        },
        {
            'name': 'port',
            'short': 'p',
            'long': 'port',
            'default': 8001,
            'type': int,
            'help': 'Port nummber (default: 8001)',
        },
    ]

    def _execute(self, options, args):
        global _site
        _site = self.site
        init_site()
        port = options and options.get('port')

        _site.template_hooks['menu'].append("""
            <li>
                <a href="#" data-toggle="modal" data-target="#newPost">New Post</a>
            </li>
            <li>
                <a href="#" data-toggle="modal" data-target="#newPage">New Page</a>
            </li>
        """)

        _site.template_hooks['menu_alt'].append(generate_menu_alt)

        _site.config['SITE_URL'] = 'http://localhost:{0}/'.format(port)
        _site.config['BASE_URL'] = 'http://localhost:{0}/'.format(port)
        _site.GLOBAL_CONTEXT['blog_url'] = 'http://localhost:{0}/'.format(port)
        _site.config['NAVIGATION_LINKS'] = {'en': []}
        _site.GLOBAL_CONTEXT['navigation_links'] = {'en': []}
        _site.config['SOCIAL_BUTTONS'] = ''
        _site.GLOBAL_CONTEXT['social_buttons_code'] = lambda _: ''
        TITLE = _site.GLOBAL_CONTEXT['blog_title']('en') + ' Administration'
        _site.config['BLOG_TITLE'] = lambda _: TITLE
        _site.GLOBAL_CONTEXT['blog_title'] = lambda _: TITLE
        _site.GLOBAL_CONTEXT['lang'] = 'en'

        if options and options.get('browser'):
            webbrowser.open('http://localhost:{0}'.format(port))
        b.run(host='localhost', port=port)

    @staticmethod
    @b.route('/')
    @b.auth_basic(auth_check, auth_title)
    def index():
        context = {}
        context['site'] = _site
        context['title'] = 'Posts & Pages'
        context['permalink'] = '/'
        return render('webapp_index.tmpl', context)

    @staticmethod
    @b.route('/edit/<path:path>', method='POST')
    @b.route('/edit/<path:path>', method='GET')
    @b.auth_basic(auth_check, auth_title)
    def edit(path):
        context = {'path': path}
        context['site'] = _site
        context['json'] = json
        post = None
        for p in _site.timeline:
            if p.source_path == path:
                post = p
                break
        if post is None:
            b.abort(404, "No such post or page")
        context['post'] = post
        context['title'] = 'Editing {0}'.format(post.title())
        context['permalink'] = '/edit/' + path
        return render('edit_post.tmpl', context)

    @staticmethod
    @b.route('/save/<path:path>', method='POST')
    @b.auth_basic(auth_check, auth_title)
    def save(path):
        # FIXME insecure pending defnull/bottle#411
        context = {'path': path}
        context['site'] = _site
        post = None
        for p in _site.timeline:
            if p.source_path == path:
                post = p
                break
        if post is None:
            b.abort(404, "No such post")
        meta = b.request.forms.decode('utf-8')
        post.compiler.create_post(post.source_path, onefile=True, is_page=False, **meta)
        init_site()
        b.redirect('/edit/' + path)

    @staticmethod
    @b.route('/delete/<path:path>')
    @b.auth_basic(auth_check, auth_title)
    def delete(path):
        context = {'path': path}
        context['site'] = _site
        post = None
        for p in _site.timeline:
            if p.source_path == path:
                post = p
                break
        if post is None:
            b.abort(404, "No such post")
        context['post'] = post
        context['title'] = 'Deleting {0}'.format(post.title())
        context['permalink'] = '/delete/' + path
        return render('delete_post.tmpl', context)

    @staticmethod
    @b.route('/really_delete/<path:path>')
    @b.auth_basic(auth_check, auth_title)
    def really_delete(path):
        # FIXME insecure pending defnull/bottle#411
        os.unlink(path)
        init_site()
        b.redirect('/')

    @staticmethod
    @b.route('/static/<path:path>')
    def server_static(path):
        return b.static_file(path, root=os.path.join(os.path.dirname(__file__), 'static'))

    @staticmethod
    @b.route('/assets/<path:path>')
    def server_assets(path):
        return b.static_file(path, root=os.path.join(_site.config["OUTPUT_FOLDER"], 'assets'))

    @staticmethod
    @b.route('/new/post', method='POST')
    @b.auth_basic(auth_check, auth_title)
    def new_post():
        title = b.request.forms.getunicode('title', encoding='utf-8')
        try:
            _site.commands.new_post(title=title, content_format='html')
        except SystemExit:
            b.abort(500, "This post already exists!")
        # reload post list and go to index
        init_site()
        b.redirect('/')

    @staticmethod
    @b.route('/new/page', method='POST')
    @b.auth_basic(auth_check, auth_title)
    def new_page():
        title = b.request.forms.getunicode('title', encoding='utf-8')
        try:
            _site.commands.new_page(title=title, content_format='html')
        except SystemExit:
            b.abort(500, "This page already exists!")
        # reload post list and go to index
        init_site()
        b.redirect('/')

    @staticmethod
    @b.route('/profile')
    @b.auth_basic(auth_check, auth_title)
    def acp_profile():
        return render('webapp_profile.tmpl',
                      context={'title': 'Edit profile',
                               'permalink': '/profile'})

    @staticmethod
    @b.route('/profile/save', method='POST')
    @b.auth_basic(auth_check, auth_title)
    def acp_profile_save():
        global USERS
        read_users()
        data = b.request.forms.decode('utf-8')
        if data['password'].strip():
            USERS[USERNAME]['password'] = passwd_hash(data['password'])
        USERS[USERNAME]['name'] = data['name']
        write_users()
        b.redirect('/profile')

def render(template_name, context=None):
    if context is None:
        context = {}
    context['USERNAME'] = USERNAME
    context['REALNAME'] = REALNAME
    return _site.render_template(template_name, None, context)
