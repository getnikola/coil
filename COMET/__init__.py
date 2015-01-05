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
import webbrowser
import io
import hashlib
import nikola.__main__
from nikola.utils import unicode_str
from flask import Flask, request, redirect, send_from_directory, g, session
from flask.ext.login import LoginManager, login_required, login_user, logout_user, current_user, make_secure_token
from flask.ext.bcrypt import Bcrypt
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
        edit_entry = '<li><a href="/users">Manage users</a></li>'
    else:
        edit_entry = ''
    return """
    <li class="dropdown">
      <a href="#" class="dropdown-toggle" data-toggle="dropdown" role="button" aria-expanded="false">{0} [{1}] <span class="caret"></span></a>
      <ul class="dropdown-menu" role="menu">
        <li><a href="/profile">Profile</a></li>
        {2}
        <li><a href="/logout">Log out</a></li>
      </ul>
    </li>""".format(current_user.realname, current_user.username, edit_entry)

def render(template_name, context=None):
    if context is None:
        context = {}
    context['g'] = g
    context['request'] = request
    context['session'] = session
    context['current_user'] = current_user
    return _site.render_template(template_name, None, context)

def unauthorized():
    return redirect('/login?status=unauthorized')

app = Flask('comet')
app.config['BCRYPT_LOG_ROUNDS'] = 12
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.unauthorized_callback = unauthorized

class User(object):
    """An user."""
    uid = -1
    username = ''
    realname = ''
    password = ''
    active = False
    is_admin = False
    can_see_others_posts = False
    want_see_others_posts = True
    can_upload_attachments = True
    can_rebuild_site = True

    def __init__(self, uid, username, realname, password, active, is_admin,
                 can_see_others_posts, want_see_others_posts,
                 can_upload_attachments, can_rebuild_site):
        self.uid = uid
        self.username = username
        self.realname = realname
        self.password = password
        self.active = active
        self.is_admin = is_admin
        self.can_see_others_posts = can_see_others_posts
        self.want_see_others_posts = want_see_others_posts
        self.can_upload_attachments = can_upload_attachments
        self.can_rebuild_site = can_rebuild_site

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
            'is_admin': user.is_admin,
            'can_see_others_posts': user.can_see_others_posts,
            'want_see_others_posts': user.want_see_others_posts,
            'can_upload_attachments': user.can_upload_attachments,
            'can_rebuild_site': user.can_rebuild_site,
        }
    with open(json_path, 'w') as fh:
        json.dump(udict, fh, indent=4)

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
            if check_password(user.password, request.form['password']) and user.active:
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
    return render('comet_login.tmpl', {'title': 'Login', 'permalink': '/login', 'alert': alert, 'alert_status': alert_status})

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login?status=logout')

@app.route('/')
@login_required
def index():
    if not os.path.exists(os.path.join(_site.config["OUTPUT_FOLDER"], 'assets')):
        return redirect('/setup')
    context = {}
    context['site'] = _site
    context['title'] = 'Posts & Pages'
    context['permalink'] = '/'
    return render('comet_index.tmpl', context)

@app.route('/setup')
def setup():
    needs_setup = not os.path.exists(os.path.join(_site.config["OUTPUT_FOLDER"], 'assets'))
    return render("comet_setup.tmpl", context={'needs_setup': needs_setup})

@app.route('/edit/<path:path>', methods=['GET', 'POST'])
@login_required
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
        return "No such post or page.", 404
    with io.open(path, 'r', encoding='utf-8') as fh:
        context['post_content'] = fh.read().split('\n\n', 1)[1]
    context['post'] = post
    context['title'] = 'Editing {0}'.format(post.title())
    context['permalink'] = '/edit/' + path
    return render('comet_post_edit.tmpl', context)

@app.route('/save/<path:path>', methods=['POST'])
@login_required
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
        return "No such post or page.", 404
    meta = {}
    for k, v in request.form.items():
        meta[k] = v
    meta.pop('_wysihtml5_mode', '')
    post.compiler.create_post(post.source_path, onefile=True, is_page=False, **meta)
    init_site()
    return redirect('/edit/' + path)

@app.route('/delete', methods=['POST'])
@login_required
def delete():
    path = request.form['path']
    for p in _site.timeline:
        if p.source_path == path:
            post = p
            break
    if post is None:
        return "No such post or page.", 404
    os.unlink(path)
    init_site()
    return redirect('/')

@app.route('/wysihtml/<path:path>')
def server_wysihtml(path):
    return send_from_directory(os.path.join(os.path.dirname(__file__), 'bower_components', 'wysihtml'), path)

@app.route('/assets/<path:path>')
def server_assets(path):
    return send_from_directory(os.path.join(_site.config["OUTPUT_FOLDER"], 'assets'), path)

@app.route('/new/post', methods=['POST'])
@login_required
def new_post():
    title = request.form['title']
    try:
        _site.commands.new_post(title=title, author=current_user.realname, content_format='html')
    except SystemExit:
        return "This post already exists!", 500
    # reload post list and go to index
    init_site()
    return redirect('/')

@app.route('/new/page', methods=['POST'])
@login_required
def new_page():
    title = request.form['title']
    try:
        _site.commands.new_page(title=title, author=current_user.realname, content_format='html')
    except SystemExit:
        return "This post already exists!", 500
    # reload post list and go to index
    init_site()
    return redirect('/')

@app.route('/profile')
@login_required
def acp_profile():
    if request.args.get('status') == 'ok':
        alert = 'Profile changed successfully.'
        alert_status = 'success'
    elif request.args.get('status') == 'pwdfail':
        alert = 'Passwords don’t match.'
        alert_status = 'danger'
    else:
        alert = ''
        alert_status = ''
    return render('comet_profile.tmpl',
                    context={'title': 'Edit profile',
                             'permalink': '/profile',
                             'alert': alert,
                             'alert_status': alert_status})

@app.route('/profile/save', methods=['POST'])
@login_required
def acp_profile_save():
    status = 'ok'
    data = request.form
    if data['newpwd1']:
        if data['newpwd1'] == data['newpwd2'] and check_password(current_user.password, data['oldpwd']):
            current_user.password = password_hash(data['newpwd1'])
        else:
            status = 'pwdfail'
    current_user.realname = data['realname']
    write_users()
    return redirect('/profile?status={0}'.format(status))

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
        return "Not authorized to edit users.", 401
    else:
        return render('comet_users.tmpl',
                        context={'title': 'Edit users',
                                 'permalink': '/users',
                                 'USERS': USERS,
                                 'alert': alert,
                                 'alert_status': alert_status})

@app.route('/users/edit', methods=['GET', 'POST'])
@login_required
def acp_users_edit():
    global USERS
    if not current_user.is_admin:
        return "Not authorized to edit users.", 401
    else:
        if request.method == 'GET':
            user = get_user(request.args.get('uid'))
        else:
            user = get_user(request.form['uid'])
        if not user:
            return "User does not exist.", 404
        new = not user.password
        if request.args.get('status') == 'ok':
            alert = 'User changed successfully.'
            alert_status = 'success'
        elif request.args.get('status') == 'ok_new':
            alert = 'User created successfully.'
            alert_status = 'success'
        elif request.args.get('status') == 'pwdfail':
            alert = 'Passwords don’t match.'
            alert_status = 'danger'
        elif request.args.get('status') == 'nopwd':
            alert = 'Must set a password.'
            alert_status = 'danger'
        else:
            alert = ''
            alert_status = ''
        return render('comet_users_edit.tmpl',
                        context={'title': 'Edit user',
                                 'permalink': '/users/edit',
                                 'user': user,
                                 'new': new,
                                 'alert': alert,
                                 'alert_status': alert_status})

@app.route('/users/save', methods=['POST'])
@login_required
def acp_users_save():
    data = request.form
    user = get_user(int(data['uid']))
    new = user.password == ''
    status = 'ok'
    if new:
        status = 'ok_new'
    if data['newpwd1']:
        if data['newpwd1'] == data['newpwd2']:
            user.password = password_hash(data['newpwd1'])
        else:
            status = 'pwdfail'
    elif new:
        status = 'nopwd'
    user.realname = data['realname']
    if user != current_user:
        user.is_admin = 'is_admin' in data
    write_users()
    return redirect('/users/edit?uid={0}&status={1}'.format(user.uid, status))


@app.route('/users/new', methods=['POST'])
@login_required
def acp_users_new():
    uid = max(USERS) + 1
    USERS[uid] = User(uid, request.form['username'], '', '', True, False, False)
    print(USERS[uid])
    return redirect('/users/{0}/edit'.format(request.form['username']))

@app.route('/users/delete', methods=['POST'])
@login_required
def acp_users_delete():
    if not current_user.is_admin:
        return "Not authorized to edit users.", 401
    else:
        user = get_user(int(request.form['uid']))
        direction = request.form['direction']
        if not user:
            return "User does not exist.", 404
        else:
            user.active = direction == 'undel'
            write_users()
            return redirect('/users?status={_del}eted'.format(_del=direction))

@app.route('/users/reload')
@login_required
def acp_users_reload():
    if not current_user.is_admin:
        return "Not authorized to edit users.", 401
    read_users()
    return redirect('/users')

def main():
    global _site, app
    nikola.__main__._RETURN_DOITNIKOLA = True
    DN = nikola.__main__.main([])
    DN.sub_cmds = DN.get_commands()
    _site = DN.nikola
    init_site()
    port = 8001

    _site.template_hooks['menu_alt'].append(generate_menu_alt)

    site = _site.config['SITE_URL']
    _site.config['SITE_URL'] = 'http://localhost:{0}/'.format(port)
    _site.config['BASE_URL'] = 'http://localhost:{0}/'.format(port)
    _site.GLOBAL_CONTEXT['blog_url'] = 'http://localhost:{0}/'.format(port)
    _site.config['NAVIGATION_LINKS'] = {'en': ((site, 'Back to {0}'.format(_site.GLOBAL_CONTEXT['blog_title']('en'))),)}
    _site.GLOBAL_CONTEXT['navigation_links'] = {'en':((site, 'Back to {0}'.format(_site.GLOBAL_CONTEXT['blog_title']('en'))),)}
    _site.config['SOCIAL_BUTTONS'] = ''
    _site.GLOBAL_CONTEXT['social_buttons_code'] = lambda _: ''
    TITLE = _site.GLOBAL_CONTEXT['blog_title']('en') + ' Administration'
    _site.config['BLOG_TITLE'] = lambda _: TITLE
    _site.GLOBAL_CONTEXT['blog_title'] = lambda _: TITLE
    _site.GLOBAL_CONTEXT['lang'] = 'en'
    app.secret_key = _site.config['COMET_SECRET_KEY']

    mod_dir = os.path.dirname(__file__)
    tmpl_dir = os.path.join(
        mod_dir, 'templates', _site.template_system.name
    )
    if os.path.isdir(tmpl_dir):
        # Inject tmpl_dir low in the theme chain
        _site.template_system.inject_directory(tmpl_dir)

    #if options and options.get('browser'):
        #webbrowser.open('http://localhost:{0}'.format(port))

    print("COMET CMS running @ http://localhost:8001/")
    app.run('localhost', port, debug=True)

if __name__ == '__main__':
    main()
