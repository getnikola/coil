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
from flask import Flask, Blueprint, request, redirect, send_from_directory
from flask.ext.login import LoginManager, login_required
_site = None
app = None
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
    REALNAME = "TEMPORARILY DISABLED"
    USERNAME = "admin"
    if USERS[USERNAME]['can_edit_users']:
        edit_entry = '<li><a href="/users">Manage users</a></li>'
    else:
        edit_entry = ''
    return """
    <li class="dropdown">
      <a href="#" class="dropdown-toggle" data-toggle="dropdown" role="button" aria-expanded="false">{0} [{1}] <span class="caret"></span></a>
      <ul class="dropdown-menu" role="menu">
        <li><a href="/profile">Profile</a></li>
        {2}
      </ul>
    </li>""".format(REALNAME, USERNAME, edit_entry)

def render(template_name, context=None):
    if context is None:
        context = {}
    context['USERNAME'] = USERNAME
    context['REALNAME'] = REALNAME
    return _site.render_template(template_name, None, context)

read_users()


# FIXME
login_required = lambda _: _

app = Flask('webapp')

@app.route('/')
@login_required
def index():
    context = {}
    context['site'] = _site
    context['title'] = 'Posts & Pages'
    context['permalink'] = '/'
    return render('webapp_index.tmpl', context)

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
    context['post'] = post
    context['title'] = 'Editing {0}'.format(post.title())
    context['permalink'] = '/edit/' + path
    return render('webapp_post_edit.tmpl', context)

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
    meta = request.form
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
    title = request.forms['title']
    try:
        _site.commands.new_post(title=title, author=REALNAME, content_format='html')
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
        _site.commands.new_page(title=title, author=REALNAME, content_format='html')
    except SystemExit:
        return "This post already exists!", 500
    # reload post list and go to index
    init_site()
    return redirect('/')

@app.route('/profile')
@login_required
def acp_profile():
    return render('webapp_profile.tmpl',
                    context={'title': 'Edit profile',
                            'permalink': '/profile'})

@app.route('/profile/save', methods=['POST'])
@login_required
def acp_profile_save():
    global USERS
    read_users()
    data = request.form
    if data['password'].strip():
        USERS[USERNAME]['password'] = passwd_hash(data['password'])
    USERS[USERNAME]['name'] = data['name']
    write_users()
    return redirect('/profile')

@app.route('/users')
@login_required
def acp_users():
    global USERS
    if not USERS[USERNAME]['can_edit_users']:
        return "Not authorized to edit users.", 401
    else:
        return render('webapp_users.tmpl',
                        context={'title': 'Edit users',
                                'permalink': '/users',
                                'USERS': USERS})
@app.route('/users/<name>')
@login_required
def acp_users_edit(name):
    global USERS
    if not USERS[USERNAME]['can_edit_users']:
        return "Not authorized to edit users.", 401
    else:
        if name in USERS:
            new = False
            user = USERS[name]
        else:
            new = True
            user = {'name': '', 'password': '', 'can_edit_users': False}
        return render('webapp_users_edit.tmpl',
                        context={'title': 'Edit user ' + name,
                                'permalink': '/users/' + name,
                                'user': user,
                                'name': name,
                                'new': new})

@app.route('/users/<name>/save', methods=['POST'])
@login_required
def acp_users_save(name):
    global USERS
    if not USERS[USERNAME]['can_edit_users']:
        return "Not authorized to edit users.", 401
    else:
        read_users()
        data = request.form
        if name not in USERS:
            USERS[name] = {'name': '', 'password': '', 'can_edit_users': False}
        if data['password'].strip():
            USERS[name]['password'] = passwd_hash(data['password'])
        USERS[name]['name'] = data['name']
        if name != USERNAME:
            USERS[name]['can_edit_users'] = 'can_edit_users' in data
        write_users()
        return redirect('/users')

@app.route('/users/create/new', methods=['POST'])
@login_required
def acp_users_create_new():
    data = request.form
    return redirect('/users/' + data['name'])

@app.route('/users/<name>/delete')
@login_required
def acp_users_delete(name):
    global USERS
    if not USERS[USERNAME]['can_edit_users']:
        return "Not authorized to edit users.", 401
    else:
        if name not in USERS:
            return "User does not exist.", 404
        return render('webapp_users_delete.tmpl',
                        context={'title': 'Deleting ' + name,
                                'permalink': '/users/{0}/delete'.format(name),
                                'user': name})

@app.route('/users/<name>/really_delete')
@login_required
def acp_users_really_delete(name):
    global USERS
    if not USERS[USERNAME]['can_edit_users']:
        return "Not authorized to edit users.", 401
    else:
        read_users()
        del USERS[name]
        write_users()
        return redirect('/users')

def main():
    global _site, app
    nikola.__main__._RETURN_SITE = True
    _site = nikola.__main__.main([])
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

    mod_dir = os.path.dirname(__file__)
    tmpl_dir = os.path.join(
        mod_dir, 'templates', _site.template_system.name
    )
    if os.path.isdir(tmpl_dir):
        # Inject tmpl_dir low in the theme chain
        _site.template_system.inject_directory(tmpl_dir)

    #if options and options.get('browser'):
        #webbrowser.open('http://localhost:{0}'.format(port))

    app.run('localhost', port, debug=True)

if __name__ == '__main__':
    main()
