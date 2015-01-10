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

from __future__ import print_function, unicode_literals
import json
import os
import io
import pkg_resources
import nikola.__main__
import logbook
from nikola.utils import unicode_str, get_logger, ColorfulStderrHandler
import nikola.plugins.command.new_post
from flask import Flask, request, redirect, send_from_directory, g, session
from flask.ext.login import (LoginManager, login_required, login_user,
                             logout_user, current_user, make_secure_token)
from flask.ext.bcrypt import Bcrypt


site = None
app = None


def scan_site():
    """Rescan the site."""
    nikola.utils.LOGGER.info("Scanning posts...")
    site.scan_posts(really=True, quiet=True)
    nikola.utils.LOGGER.info("Posts scanned.")


def configure_url(url):
    """Configure site URL."""
    app.config['COMET_URL'] = site.config['SITE_URL'] =\
        site.config['BASE_URL'] = site.GLOBAL_CONTEXT['blog_url'] = url


def configure_site():
    """Configure the site for Comet."""
    global site

    nikola.__main__._RETURN_DOITNIKOLA = True
    _dn = nikola.__main__.main([])
    _dn.sub_cmds = _dn.get_commands()
    site = _dn.nikola
    app.config['NIKOLA_ROOT'] = os.getcwd()
    app.config['DEBUG'] = False
    app.config['USERS'] = {}
    app.config['USERS_PATH'] = os.path.join(app.config['NIKOLA_ROOT'],
                                            'comet_users.json')

    logf = (u'[{record.time:%Y-%m-%dT%H:%M:%SZ}] {record.level_name}: '
            u'{record.channel}: {record.message}')
    logh = (u'[{record.time:%Y-%m-%dT%H:%M:%SZ}] {record.channel} '
            u'{record.message}')

    loghandlers = [
        ColorfulStderrHandler(level=logbook.DEBUG, format_string=logf,
                              bubble=True),
        logbook.FileHandler('comet.log', 'a', 'utf-8', logbook.DEBUG, logf,
                            bubble=True)
    ]

    hloghandlers = [
        ColorfulStderrHandler(level=logbook.DEBUG, format_string=logh,
                              bubble=True),
        logbook.FileHandler('comet.log', 'a', 'utf-8', logbook.DEBUG, logh,
                            bubble=True)
    ]

    site.loghandlers = loghandlers
    nikola.utils.LOGGER.handlers = loghandlers

    nikola.plugins.command.new_post.POSTLOGGER.handlers = loghandlers
    nikola.plugins.command.new_post.PAGELOGGER.handlers = loghandlers

    app.config['LOGGER_NAME'] = 'Comet'
    app._logger = get_logger('Comet', loghandlers)
    app.http_logger = get_logger('CometHTTP', hloghandlers)

    if site.configured:
        scan_site()
    else:
        raise Exception("Not a Nikola site.")

    app.secret_key = site.config.get('COMET_SECRET_KEY')
    app.config['COMET_URL'] = site.config.get('COMET_URL')

    read_users()

    site.template_hooks['menu_alt'].append(generate_menu_alt)

    app.config['NIKOLA_URL'] = site.config['SITE_URL']
    configure_url(app.config['COMET_URL'])
    site.config['NAVIGATION_LINKS'] = {
        'en': (
            (app.config['NIKOLA_URL'],
             '<i class="fa fa-globe"></i> Back to website'),
            ('/rebuild', '<i class="fa fa-cog rebuild"></i> Rebuild'),
        )
    }
    site.GLOBAL_CONTEXT['navigation_links'] = site.config['NAVIGATION_LINKS']
    TITLE = site.GLOBAL_CONTEXT['blog_title']('en') + ' Administration'
    site.config['BLOG_TITLE'] = lambda _: TITLE
    site.GLOBAL_CONTEXT['blog_title'] = lambda _: TITLE
    site.GLOBAL_CONTEXT['lang'] = 'en'
    site.GLOBAL_CONTEXT['extra_head_data'] = lambda _: (
        """<link href="//maxcdn.bootstrapcdn.com/font-awesome/4.2.0/css/"""
        """font-awesome.min.css" rel="stylesheet">
    <link href="/comet_assets/css/comet.css" rel="stylesheet">""")
    # HACK: body_end appears after extra_js from templates, so we must use
    #       social_buttons_code instead
    site.GLOBAL_CONTEXT['social_buttons_code'] = lambda _: """
    <script src="/comet_assets/js/comet.js"></scripts>
    """

    tmpl_dir = pkg_resources.resource_filename(
        'comet', os.path.join('data', 'templates', site.template_system.name))
    if os.path.isdir(tmpl_dir):
        # Inject tmpl_dir low in the theme chain
        site.template_system.inject_directory(tmpl_dir)


def password_hash(password):
    """Hash the password, using bcrypt.

    :param str password: Password in plaintext
    :return: password hash
    :rtype: str
    """
    return bcrypt.generate_password_hash(password)


def check_password(pwdhash, password):
    """Check the password hash from :func:`password_hash`.

    :param str pwdhash: Hash from :func:`password_hash` to check
    :param str password: Password in plaintext
    :return: password match
    :rtype: bool
    """
    return bcrypt.check_password_hash(pwdhash, password)


def generate_menu_alt():
    """Generate ``menu_alt`` with log in/out links.

    :return: HTML fragment
    :rtype: str
    """
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
    """Get the name of the post author.

    :param Post post: The post object to determine authorship of
    :return: Author real name
    :rtype: str
    """
    a = post.meta['en']['author']
    return a if a else current_user.realname


def _author_uid_get(post):
    """Get the UID of the post author.

    :param Post post: The post object to determine authorship of
    :return: Author UID
    :rtype: str
    """
    u = post.meta['en']['author.uid']
    return u if u else str(current_user.uid)


def render(template_name, context=None, code=200, headers=None):
    """Render a response using standard Nikola templates.

    :param str template_name: Template name
    :param dict context: Context (variables) to use in the template
    :param int code: HTTP status code
    :param headers: Headers to use for the response
    :return: HTML fragment
    :rtype: str
    """
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

    return site.render_template(template_name, None, context), code, headers


def error(desc, code, permalink):
    """Render an error page.

    :param str desc: Error description
    :param int code: HTTP status code
    :param str permalink: Path to page generating errors
    :return: HTML fragment (from :func:`render`)
    :rtype: str
    """
    return render('comet_error.tmpl',
                  {'title': 'Error',
                   'code': code,
                   'desc': desc,
                   'permalink': permalink},
                  code)


def _unauthorized():
    """Redirect to the “unauthorized” page."""
    return redirect('/login?status=unauthorized')


def find_post(path):
    """Find a post.

    :param str path: Path to the post
    :return: A post matching the path
    :rtype: Post or None
    """
    for p in site.timeline:
        if p.source_path == path:
            return p
    return None


app = Flask('comet')
app.config['BCRYPT_LOG_ROUNDS'] = 12


@app.after_request
def log_request(resp):
    """Log a request."""
    l = "[{4}] {0} {1} {2} <{3}>".format(request.remote_addr, request.method,
                                         request.url, request.endpoint,
                                         resp.status_code)
    c = str(resp.status_code)[0]
    if c in ['1', '2'] or resp.status_code == 304:
        app.http_logger.info(l)
    elif c == '3':
        app.http_logger.warn(l)
    else:
        app.http_logger.error(l)
    return resp

bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.unauthorized_callback = _unauthorized
PERMISSIONS = ['is_admin', 'can_edit_all_posts', 'wants_all_posts',
               'can_upload_attachments', 'can_rebuild_site',
               'can_transfer_post_authorship']


class User(object):
    """An user.  Compatible with Flask-Login."""
    def __init__(self, uid, username, realname, password, active, is_admin,
                 can_edit_all_posts, wants_all_posts,
                 can_upload_attachments, can_rebuild_site,
                 can_transfer_post_authorship):
        """Initialize an user with specified settings."""
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
        """Get user ID."""
        return unicode_str(self.uid)

    def is_authenticated(self):
        """Check whether user is authorized to log in."""
        return self.active

    def is_active(self):
        """Check whether user is active."""
        return self.active

    def is_anonymous(self):
        """Check whether user is anonymous."""
        return not self.active

    def get_auth_token(self):
        """Generate an authentication token."""
        return make_secure_token(self.uid, self.username, self.password)

    def __repr__(self):
        """Return a programmer-friendly representation."""
        return '<User {0}>'.format(self.username)


@login_manager.user_loader
def get_user(uid):
    """Get an user by the UID.

    :param str uid: UID to find
    :return: the user
    :rtype: User object
    :raises ValueError: uid is not an integer
    :raises KeyError: if user does not exist
    """
    return app.config['USERS'][int(uid)]


def find_user_by_name(username):
    """Get an user by their username.

    :param str username: Username to find
    :return: the user
    :rtype: User object or None
    """
    for uid, u in app.config['USERS'].items():
        if u.username == username:
            return u
            break


def read_users():
    """Read user data from the JSON file."""
    app.config['USERS'] = {}

    if not os.path.exists(app.config['USERS_PATH']):
        raise Exception("Cannot find comet_users.json.")

    with io.open(app.config['USERS_PATH'], 'r', encoding='utf-8') as fh:
        udict = json.load(fh)
    for uid, data in udict.items():
        uid = int(uid)
        app.config['USERS'][uid] = User(uid, **data)


def write_users():
    """Write user data to the JSON file."""
    udict = {}
    for uid, user in app.config['USERS'].items():
        uid = unicode_str(uid)
        udict[uid] = {
            'username': user.username,
            'realname': user.realname,
            'password': user.password,
            'active': user.active,
        }
        for p in PERMISSIONS:
            udict[uid][p] = getattr(user, p)
    with open(app.config['USERS_PATH'], 'w') as fh:
        json.dump(udict, fh, indent=4, sort_keys=True, separators=(',', ': '))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user authentication.

    If requested over GET, present login page.
    If requested over POST, log user in.

    :param str status: Status of previous request/login attempt
    """
    alert = None
    alert_status = 'danger'
    code = 200
    if request.method == 'POST':
        user = find_user_by_name(request.form['username'])
        if not user:
            alert = 'Invalid credentials.'
            code = 401
        else:
            if check_password(user.password,
                              request.form['password']) and user.active:
                login_user(user, remember=('remember-me' in request.form))
                return redirect('/')
            else:
                alert = "Invalid credentials."
                code = 401
    else:
        if request.args.get('status') == 'unauthorized':
            alert = 'Please log in to access this page.'
        elif request.args.get('status') == 'logout':
            alert = 'Logged out successfully.'
            alert_status = 'success'
    return render('comet_login.tmpl', {'title': 'Login', 'permalink': '/login',
                                       'alert': alert,
                                       'alert_status': alert_status}, code)


@app.route('/logout')
@login_required
def logout():
    """Log the user out and redirect them to the login page."""
    logout_user()
    return redirect('/login?status=logout')


@app.route('/')
@login_required
def index():
    """Show the index with all posts.

    :param int all: Whether or not should show all posts
    """
    if not os.path.exists(os.path.join(site.config["OUTPUT_FOLDER"],
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
        posts = site.posts
        pages = site.pages
    else:
        wants = False
        posts = []
        pages = []
        for p in site.timeline:
            if (p.meta('author.uid')
                    and p.meta('author.uid') != str(current_user.uid)):
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


# TODO: delete (with redirects) as soon as `comet init` and real docs exist
@app.route('/setup')
def setup():
    """TEMPORARY setup function."""
    ns = not os.path.exists(os.path.join(site.config["OUTPUT_FOLDER"],
                                         'assets'))
    return render("comet_setup.tmpl", context={'needs_setup': ns})


@app.route('/edit/<path:path>', methods=['GET', 'POST'])
@login_required
def edit(path):
    """Edit a post.

    If requested over GET, shows the edit UI.
    If requested over POST, saves the post and shows the edit UI.

    :param path: Path to post to edit.
    """
    context = {'path': path, 'site': site}
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
        scan_site()
        post = find_post(path)
        context['action'] = 'save'
        context['post_content'] = meta['content']
    else:
        context['action'] = 'edit'
        with io.open(path, 'r', encoding='utf-8') as fh:
            context['post_content'] = fh.read().split('\n\n', 1)[1]

    context['post'] = post
    safe_users = []
    for u in app.config['USERS'].values():
        safe_users.append((u.uid, u.realname))
    context['USERS'] = sorted(safe_users)
    context['current_auid'] = int(post.meta('author.uid') or current_user.uid)
    context['title'] = 'Editing {0}'.format(post.title())
    context['permalink'] = '/edit/' + path
    return render('comet_post_edit.tmpl', context)


@app.route('/delete', methods=['POST'])
@login_required
def delete():
    """Delete a post."""
    path = request.form['path']
    for p in site.timeline:
        if p.source_path == path:
            post = p
            break
    if post is None:
        return error("No such post or page.", 404, '/delete')
    os.unlink(path)
    scan_site()
    return redirect('/')


@app.route('/rebuild')
@login_required
def rebuild():
    """Rebuild the site."""
    return "<h1>Not implemented.</h1>", 500


@app.route('/rescan')
@login_required
def rescan():
    """Rescan posts."""
    scan_site()
    return redirect('/')


@app.route('/wysihtml/<path:path>')
def serve_wysihtml(path):
    """Serve wysihtml files.

    This is meant to be used ONLY by the internal dev server.
    Please configure your web server to handle requests to this URL::

        /wysihtml/ => comet/data/bower_components/wysihtml
    """
    res = pkg_resources.resource_filename(
        'comet', os.path.join('data', 'bower_components', 'wysihtml'))
    return send_from_directory(res, path)


@app.route('/comet_assets/<path:path>')
def serve_comet_assets(path):
    """Serve Comet assets.

    This is meant to be used ONLY by the internal dev server.
    Please configure your web server to handle requests to this URL::

        /comet_assets/ => comet/data/comet_assets
    """
    res = pkg_resources.resource_filename(
        'comet', os.path.join('data', 'comet_assets'))
    return send_from_directory(res, path)


@app.route('/assets/<path:path>')
def serve_assets(path):
    """Serve Nikola assets.

    This is meant to be used ONLY by the internal dev server.
    Please configure your web server to handle requests to this URL::

        /assets/ => output/assets
    """
    res = os.path.join(app.config['NIKOLA_ROOT'],
                       site.config["OUTPUT_FOLDER"], 'assets')
    return send_from_directory(res, path)


@app.route('/new/<obj>', methods=['POST'])
@login_required
def new(obj):
    """Create a new post or page.

    :param str obj: Object to create (post or page)
    """
    title = request.form['title']
    site.config['ADDITIONAL_METADATA']['author.uid'] = current_user.uid
    try:
        if obj == 'post':
            site.commands.new_post(title=title, author=current_user.realname,
                                   content_format='html')
        elif obj == 'page':
            site.commands.new_page(title=title, author=current_user.realname,
                                   content_format='html')
        else:
            return error("Cannot create {0} — unknown type.".format(obj),
                         400, '/new/' + obj)
    except SystemExit:
        return error("This {0} already exists!".format(obj),
                     500, '/new/' + obj)
    finally:
        del site.config['ADDITIONAL_METADATA']['author.uid']
    # reload post list and go to index
    scan_site()
    return redirect('/')


@app.route('/account', methods=['POST', 'GET'])
@login_required
def acp_user_account():
    """Manage the user account of currently-logged-in users.

    This does NOT accept admin-specific options.
    """
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
    """List all users."""
    alert = ''
    alert_status = ''
    if request.args.get('status') == 'deleted':
        alert = 'User deleted.'
        alert_status = 'success'
    if request.args.get('status') == 'undeleted':
        alert = 'User undeleted.'
        alert_status = 'success'
    if not current_user.is_admin:
        return error("Not authorized to edit users.", 401, "/users")
    else:
        return render('comet_users.tmpl',
                      context={'title': 'Users',
                               'permalink': '/users',
                               'USERS': app.config['USERS'],
                               'alert': alert,
                               'alert_status': alert_status})


@app.route('/users/edit', methods=['POST'])
@login_required
def acp_users_edit():
    """Edit an user account."""
    if not current_user.is_admin:
        return error("Not authorized to edit users.", 401, "/users/edit")
    data = request.form
    action = data['action']

    if action == 'new':
        uid = max(app.config['USERS']) + 1
        app.config['USERS'][uid] = User(uid, data['username'], '', '', True,
                                        False, True, True, True, True)
        user = app.config['USERS'][uid]
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
    """Delete or undelete an user account."""
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
    """Change user permissions."""
    if not current_user.is_admin:
        return error("Not authorized to edit users.",
                     401, "/users/permissions")

    if request.method == 'POST':
        for uid, user in app.config['USERS'].items():
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
        d = ('<input type="checkbox" name="{0}.{1}" data-uid="{0}" '
             'data-perm="{1}" class="u{0}" {2} {3}>')
        return d.format(user.uid, permission, checked, disabled)

    return render('comet_users_permissions.tmpl',
                  context={'title': 'Permissions',
                           'permalink': '/users/permissions',
                           'USERS': app.config['USERS'],
                           'PERMISSIONS': PERMISSIONS,
                           'action': action,
                           'json': json,
                           'display_permission': display_permission})

configure_site()