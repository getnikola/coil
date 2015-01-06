# -*- coding: utf-8 -*-

# Copyright © 2014-2015 Roberto Alsina, Henry Hirsch, Chris Warrick.

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
import sys
import webbrowser
import io
import nikola.__main__
from nikola.utils import unicode_str
from flask import Flask, request, redirect, send_from_directory, g, session
from flask.ext.login import (LoginManager, login_required, login_user,
                             logout_user, current_user, make_secure_token)
from flask.ext.bcrypt import Bcrypt

__version__ = '0.5.0'

_site = None
app = None
TITLE = 'comet'
USERS = {}
auth_title = 'Comet CMS Login'

json_path = os.path.join(os.path.dirname(__file__), 'users.json')

def init_site():
    _site.scan_posts(really=True)

def password_hash(password):
    return bcrypt.generate_password_hash(password)

def check_password(hash, password):
    return bcrypt.check_password_hash(hash, password)

def generate_menu_alt():
    if not current_user.is_authenticated():
        return """<li><a href="/login">Log in</a></li>"""
    if current_user.is_admin:
        edit_entry = """<li><a href="/users">Manage users</a></li>\
        <li><a href="/users/permissions">Permissions</a></li>"""
    else:
        edit_entry = ''
    return """
    <li class="dropdown">
        <a href="#" class="dropdown-toggle" data-toggle="dropdown"
            role="button" aria-expanded="false">{0} [{1}]<span
            class="caret"></span></a>
        <ul class="dropdown-menu" role="menu">
            <li><a href="/account">Account</a></li>
            {2}
            <li><a href="/logout">Log out</a></li>
        </ul>
    </li>""".format(current_user.realname, current_user.username, edit_entry)

def _author_get(post):
    a = post.meta['en']['author']
    return a if a else current_user.realname

def _author_uid_get(post):
    u = post.meta['en']['author.uid']
    return u if u else current_user.uid

def render(template_name, context=None, code=200, headers=None):
    if context is None:
        context = {}
    if headers is None:
        headers = {}

    context['g'] = g
    context['request'] = request
    context['session'] = session
    context['current_user'] = current_user
    context['_author_get'] = _author_get
    context['_author_uid_get'] = _author_uid_get

    headers['Pragma'] = 'no-cache'
    headers['Cache-Control'] = 'private, max-age=0, no-cache'

    return _site.render_template(template_name, None, context), code, headers

def error(desc, code, permalink):
    return render('comet_error.tmpl', {'title': 'Error', 'code': code, 'desc': desc, 'permalink': permalink}, code)


def unauthorized():
    return redirect('/login?status=unauthorized')

def find_post(path):
    for p in _site.timeline:
        if p.source_path == path:
            return p
    return None

app = Flask('comet')
app.config['BCRYPT_LOG_ROUNDS'] = 12
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.unauthorized_callback = unauthorized
PERMISSIONS = ['is_admin', 'can_edit_all_posts', 'wants_all_posts',
               'can_upload_attachments', 'can_rebuild_site',
               'can_transfer_post_authorship']

class User(object):
    """An user."""
    def __init__(self, uid, username, realname, password, active, is_admin,
                 can_edit_all_posts, wants_all_posts,
                 can_upload_attachments, can_rebuild_site,
                 can_transfer_post_authorship):
        self.uid = uid
        self.username = username
        self.realname = realname
        self.password = password
        self.active = active
        self.is_admin = is_admin
        self.can_edit_all_posts = can_edit_all_posts
        self.wants_all_posts = wants_all_posts
        self.can_upload_attachments = can_upload_attachments
        self.can_rebuild_site = can_rebuild_site
        self.can_transfer_post_authorship = can_transfer_post_authorship

    def get_id(self):
        return unicode_str(self.uid)

    def is_authenticated(self):
        return self.active

    def is_active(self):
        return self.active

    def is_anonymous(self):
        return not self.active

    def get_auth_token(self):
        return make_secure_token(self.uid, self.username, self.password)

    def __repr__(self):
        return '<User {0}>'.format(self.username)

@login_manager.user_loader
def get_user(uid):
    global USERS
    return USERS[int(uid)]

def find_user_by_name(username):
        for uid, u in USERS.items():
            if u.username == username:
                return u
                break

def read_users():
    global USERS
    USERS = {}
    with io.open(json_path, 'r', encoding='utf-8') as fh:
        udict = json.load(fh)
    for uid, data in udict.items():
        uid = int(uid)
        USERS[uid] = User(uid, **data)

def write_users():
    global USERS
    udict = {}
    for uid, user in USERS.items():
        uid = unicode_str(uid)
        udict[uid] = {
            'username': user.username,
            'realname': user.realname,
            'password': user.password,
            'active': user.active,
        }
        for p in PERMISSIONS:
            udict[uid][p] = getattr(user, p)
    with open(json_path, 'w') as fh:
        json.dump(udict, fh, indent=4, sort_keys=True, separators=(',', ': '))

read_users()

@app.route('/login', methods=['GET', 'POST'])
def login():
    alert = None
    alert_status = 'danger'
    if request.method == 'POST':
        user = find_user_by_name(request.form['username'])
        if not user:
            alert = 'Invalid credentials.'
        else:
            if check_password(user.password,
                              request.form['password']) and user.active:
                login_user(user, remember=('remember-me' in request.form))
                return redirect('/')
            else:
                alert = "Invalid credentials."
    else:
        if request.args.get('status') == 'unauthorized':
            alert = 'Please log in to access this page.'
        elif request.args.get('status') == 'logout':
            alert = 'Logged out successfully.'
            alert_status = 'success'
    return render('comet_login.tmpl', {'title': 'Login', 'permalink': '/login',
                                       'alert': alert,
                                       'alert_status': alert_status})

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login?status=logout')

@app.route('/')
@login_required
def index():
    if not os.path.exists(os.path.join(_site.config["OUTPUT_FOLDER"],
                                       'assets')):
        return redirect('/setup')
    context = {}

    n = request.args.get('all')
    if n is None:
        wants_now = None
    else:
        wants_now = n == '1'

    if wants_now is None and current_user.wants_all_posts:
        wants = True
    else:
        wants = wants_now

    if current_user.can_edit_all_posts and wants:
        posts = _site.posts
        pages = _site.pages
    else:
        wants = False
        posts = []
        pages = []
        for p in _site.timeline:
            if p.meta('author.uid') and p.meta('author.uid') != str(current_user.uid):
                continue
            if p.use_in_feeds:
                posts.append(p)
            else:
                pages.append(p)

    context['posts'] = posts
    context['pages'] = pages
    context['title'] = 'Posts & Pages'
    context['permalink'] = '/'
    context['wants'] = wants
    return render('comet_index.tmpl', context)

@app.route('/setup')
def setup():
    ns = not os.path.exists(os.path.join(_site.config["OUTPUT_FOLDER"],
                                         'assets'))
    return render("comet_setup.tmpl", context={'needs_setup': ns})

@app.route('/edit/<path:path>', methods=['GET', 'POST'])
@login_required
def edit(path):
    context = {'path': path, 'site': _site}
    post = find_post(path)
    if post is None:
        return error("No such post or page.", 404, '/edit/' + path)

    if request.method == 'POST':
        meta = {}
        for k, v in request.form.items():
            meta[k] = v
        meta.pop('_wysihtml5_mode', '')
        try:
            meta['author'] = get_user(int(meta['author.uid'])).realname
            author_change_success = True
        except:
            author_change_success = False
        if (not current_user.can_transfer_post_authorship
            or not author_change_success):
            meta['author'] = post.meta('author') or current_user.realname
            meta['author.uid'] = post.meta('author.uid') or current_user.uid
        post.compiler.create_post(post.source_path, onefile=True,
                                  is_page=False, **meta)
        init_site()
        post = find_post(path)
        context['action'] = 'save'
        context['post_content'] = meta['content']
    else:
        context['action'] = 'edit'
        with io.open(path, 'r', encoding='utf-8') as fh:
            context['post_content'] = fh.read().split('\n\n', 1)[1]

    context['post'] = post
    safe_users = []
    for u in USERS.values():
        safe_users.append((u.uid, u.realname))
    context['USERS'] = sorted(safe_users)
    context['current_auid'] = int(post.meta('author.uid') or current_user.uid)
    context['title'] = 'Editing {0}'.format(post.title())
    context['permalink'] = '/edit/' + path
    return render('comet_post_edit.tmpl', context)

@app.route('/delete', methods=['POST'])
@login_required
def delete():
    path = request.form['path']
    for p in _site.timeline:
        if p.source_path == path:
            post = p
            break
    if post is None:
        return error("No such post or page.", 404, '/delete')
    os.unlink(path)
    init_site()
    return redirect('/')

# Please do those in nginx if possible.
@app.route('/wysihtml/<path:path>')
def serve_wysihtml(path):
    return send_from_directory(os.path.join(os.path.dirname(__file__),
                                            'bower_components', 'wysihtml'),
                               path)

@app.route('/comet_assets/<path:path>')
def serve_comet_assets(path):
    return send_from_directory(os.path.join(os.path.dirname(__file__),
                                            'comet_assets'), path)

@app.route('/assets/<path:path>')
def serve_assets(path):
    return send_from_directory(os.path.join(_site.config["OUTPUT_FOLDER"],
                                            'assets'), path)

@app.route('/new/<obj>', methods=['POST'])
@login_required
def new_post_or_page(obj):
    title = request.form['title']
    _site['ADDITIONAL_METADATA']['author.uid'] = current_user.uid
    try:
        if obj == 'post':
            _site.commands.new_post(title=title, author=current_user.realname,
                                    content_format='html')
        elif obj == 'page':
            _site.commands.new_page(title=title, author=current_user.realname,
                                    content_format='html')
        else:
            return error("Cannot create {0} — unknown type.".format(obj), 400, '/new/' + obj)
    except SystemExit:
        return error("This {0} already exists!".format(obj), 500, '/new/' + obj)
    finally:
        del _site['ADDITIONAL_METADATA']['author.uid']
    # reload post list and go to index
    init_site()
    return redirect('/')

@app.route('/account', methods=['POST', 'GET'])
@login_required
def acp_user_account():
    alert = ''
    alert_status = ''
    action = 'edit'
    if request.method == 'POST':
        action = 'save'
        data = request.form
        if data['newpwd1']:
            if data['newpwd1'] == data['newpwd2'] and check_password(
                    current_user.password, data['oldpwd']):
                current_user.password = password_hash(data['newpwd1'])
            else:
                alert = 'Passwords don’t match.'
                alert_status = 'danger'
                action = 'save_fail'
        current_user.realname = data['realname']
        current_user.wants_all_posts = 'wants_all_posts' in data
        write_users()


    return render('comet_account.tmpl',
                    context={'title': 'My account',
                             'permalink': '/account',
                             'action': action,
                             'alert': alert,
                             'alert_status': alert_status})

@app.route('/users')
@login_required
def acp_users():
    alert = ''
    alert_status = ''
    if request.args.get('status') == 'deleted':
        alert = 'User deleted.'
        alert_status = 'success'
    if request.args.get('status') == 'undeleted':
        alert = 'User undeleted.'
        alert_status = 'success'
    global USERS
    if not current_user.is_admin:
        return error("Not authorized to edit users.", 401, "/users")
    else:
        return render('comet_users.tmpl',
                        context={'title': 'Users',
                                 'permalink': '/users',
                                 'USERS': USERS,
                                 'alert': alert,
                                 'alert_status': alert_status})

@app.route('/users/edit', methods=['POST'])
@login_required
def acp_users_edit():
    global USERS
    if not current_user.is_admin:
        return error("Not authorized to edit users.", 401, "/users/edit")
    data = request.form
    action = data['action']

    if action == 'new':
        uid = max(USERS) + 1
        USERS[uid] = User(uid, data['username'], '', '', True, False, True,
                          True, True, True)
        user = USERS[uid]
        new = True
    else:
        user = get_user(data['uid'])
        new = False

    if not user:
        return error("User does not exist.", 404, "/users/edit")

    alert = ''
    alert_status = ''

    if action == 'save':
        if data['newpwd1']:
            if data['newpwd1'] == data['newpwd2']:
                user.password = password_hash(data['newpwd1'])
            else:
                alert = 'Passwords don’t match.'
                alert_status = 'danger'
                action = 'save_fail'
        elif new:
            alert = 'Must set a password.'
            alert_status = 'danger'
            action = 'save_fail'
        user.realname = data['realname']
        for p in PERMISSIONS:
            setattr(user, p, p in data)
        if user == current_user:
            user.is_admin = True

        write_users()

    return render('comet_users_edit.tmpl',
                    context={'title': 'Edit user',
                             'permalink': '/users/edit',
                             'user': user,
                             'new': new,
                             'action': action,
                             'alert': alert,
                             'alert_status': alert_status})

@app.route('/users/delete', methods=['POST'])
@login_required
def acp_users_delete():
    if not current_user.is_admin:
        return error("Not authorized to edit users.", 401, "/users/delete")
    user = get_user(int(request.form['uid']))
    direction = request.form['direction']
    if not user:
        return error("User does not exist.", 404, "/users/edit/delete")
    else:
        user.active = direction == 'undel'
        for p in PERMISSIONS:
            setattr(user, p, False)
        write_users()
        return redirect('/users?status={_del}eted'.format(_del=direction))

@app.route('/users/permissions', methods=['GET', 'POST'])
@login_required
def acp_users_permissions():
    global USERS
    if not current_user.is_admin:
        return error("Not authorized to edit users.", 401, "/users/permissions")


    if request.method == 'POST':
        for uid, user in USERS.items():
            for perm in PERMISSIONS:
                if '{0}.{1}'.format(uid, perm) in request.form:
                    setattr(user, perm, True)
                else:
                    setattr(user, perm, False)
        current_user.is_admin = True  # cannot deadmin oneself
        action = 'save'
        write_users()
    else:
        action = 'edit'

    def display_permission(user, permission):
        checked = 'checked' if getattr(user, permission) else ''
        if permission == 'wants_all_posts' and not user.can_edit_all_posts:
            # If this happens, permissions are damaged.
            checked = ''
        if user == current_user and permission == 'is_admin':
            disabled = 'disabled'
        else:
            disabled = ''
        return """<input type="checkbox" name="{0}.{1}" data-uid="{0}" data-perm="{1}" class="u{0}" {2} {3}>""".format(
            user.uid, permission, checked, disabled)

    return render('comet_users_permissions.tmpl',
                    context={'title': 'Permissions',
                             'permalink': '/users/permissions',
                             'USERS': USERS,
                             'PERMISSIONS': PERMISSIONS,
                             'action': action,
                             'json': json,
                             'display_permission': display_permission})


@app.route('/users/reload')
def acp_users_reload():
    read_users()
    return redirect('/users')

nikola.__main__._RETURN_DOITNIKOLA = True
DN = nikola.__main__.main([])
DN.sub_cmds = DN.get_commands()
_site = DN.nikola
init_site()

_site.template_hooks['menu_alt'].append(generate_menu_alt)
PORT = 8001

site = _site.config['SITE_URL']
_site.config['SITE_URL'] = 'http://localhost:{0}/'.format(PORT)
_site.config['BASE_URL'] = 'http://localhost:{0}/'.format(PORT)
_site.GLOBAL_CONTEXT['blog_url'] = 'http://localhost:{0}/'.format(PORT)
_site.config['NAVIGATION_LINKS'] = {'en': ((site, 'Back to {0}'.format(
    _site.GLOBAL_CONTEXT['blog_title']('en'))),)}
_site.GLOBAL_CONTEXT['navigation_links'] = {'en':((site, 'Back to {0}'.format(
    _site.GLOBAL_CONTEXT['blog_title']('en'))),)}
TITLE = _site.GLOBAL_CONTEXT['blog_title']('en') + ' Administration'
_site.config['BLOG_TITLE'] = lambda _: TITLE
_site.GLOBAL_CONTEXT['blog_title'] = lambda _: TITLE
_site.GLOBAL_CONTEXT['lang'] = 'en'
_site.GLOBAL_CONTEXT['extra_head_data'] = lambda _: """
<link href="//maxcdn.bootstrapcdn.com/font-awesome/4.2.0/\
css/font-awesome.min.css" rel="stylesheet">
<link href="/comet_assets/css/comet.css" rel="stylesheet">
"""
# HACK: body_end appears after extra_js from templates, so we must use
#       social_buttons_code instead
_site.GLOBAL_CONTEXT['social_buttons_code'] = lambda _: """
<script src="/comet_assets/js/comet.js"></scripts>
"""

app.secret_key = _site.config['COMET_SECRET_KEY']

mod_dir = os.path.dirname(__file__)
tmpl_dir = os.path.join(
    mod_dir, 'templates', _site.template_system.name
)
if os.path.isdir(tmpl_dir):
    # Inject tmpl_dir low in the theme chain
    _site.template_system.inject_directory(tmpl_dir)

def main():
    global _site
    port = 8001
    _site.config['SITE_URL'] = 'http://localhost:{0}/'.format(port)
    _site.config['BASE_URL'] = 'http://localhost:{0}/'.format(port)
    _site.GLOBAL_CONTEXT['blog_url'] = 'http://localhost:{0}/'.format(port)
    if '-h' in sys.argv:
        print("COMET CMS v{0}".format(__version__))
        print("")
        print("  -b     Open a web browser after starting.")
    elif '-v' in sys.argv:
        print("COMET CMS v{0}".format(__version__))
    else:
        if '-b' in sys.argv:
                webbrowser.open('http://localhost:{0}'.format(port))

        print("COMET CMS running @ http://localhost:8001/")
        app.run('localhost', port, debug=True)

if __name__ == '__main__':
    main()
