# -*- coding: utf-8 -*-

# Coil CMS v1.0.0
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
import sys
import io
import pkg_resources
import nikola.__main__
import logbook
import redis
import rq
import coil.tasks
from nikola.utils import (unicode_str, get_logger, ColorfulStderrHandler,
                          write_metadata, TranslatableSetting)
import nikola.plugins.command.new_post
from flask import Flask, request, redirect, send_from_directory, g, session
from flask.ext.login import (LoginManager, login_required, login_user,
                             logout_user, current_user, make_secure_token)
from flask.ext.bcrypt import Bcrypt
from coil.utils import USER_FIELDS, PERMISSIONS, SiteProxy
from coil.forms import (LoginForm, NewPostForm, NewPageForm, DeleteForm,
                         UserDeleteForm, UserEditForm, AccountForm,
                         PermissionsForm)

_site = None
site = None
app = None
db = None
q = None


def scan_site():
    """Rescan the site."""
    site.scan_posts(really=True, quiet=True)


def configure_url(url):
    """Configure site URL."""
    app.config['COIL_URL'] = \
        _site.config['SITE_URL'] = _site.config['BASE_URL'] =\
        _site.GLOBAL_CONTEXT['blog_url'] =\
        site.config['SITE_URL'] = site.config['BASE_URL'] =\
        url


def configure_site():
    """Configure the Nikola site for Coil CMS."""
    global _site, site, db, q

    nikola.__main__._RETURN_DOITNIKOLA = True
    _dn = nikola.__main__.main([])
    _dn.sub_cmds = _dn.get_commands()
    _site = _dn.nikola
    app.config['BCRYPT_LOG_ROUNDS'] = 12
    app.config['NIKOLA_ROOT'] = os.getcwd()
    app.config['DEBUG'] = False

    # Logging configuration

    logf = (u'[{record.time:%Y-%m-%dT%H:%M:%SZ}] {record.level_name}: '
            u'{record.channel}: {record.message}')
    logh = (u'[{record.time:%Y-%m-%dT%H:%M:%SZ}] {record.channel} '
            u'{record.message}')

    loghandlers = [
        ColorfulStderrHandler(level=logbook.DEBUG, format_string=logf,
                              bubble=True),
        logbook.FileHandler('coil.log', 'a', 'utf-8', logbook.DEBUG, logf,
                            bubble=True)
    ]

    hloghandlers = [
        ColorfulStderrHandler(level=logbook.DEBUG, format_string=logh,
                              bubble=True),
        logbook.FileHandler('coil.log', 'a', 'utf-8', logbook.DEBUG, logh,
                            bubble=True)
    ]

    _site.loghandlers = loghandlers
    nikola.utils.LOGGER.handlers = loghandlers

    nikola.plugins.command.new_post.POSTLOGGER.handlers = loghandlers
    nikola.plugins.command.new_post.PAGELOGGER.handlers = loghandlers

    app.config['LOGGER_NAME'] = 'Coil'
    app._logger = get_logger('Coil', loghandlers)
    app.http_logger = get_logger('CoilHTTP', hloghandlers)

    if not _site.configured:
        app.logger("Not a Nikola site.")
        return

    app.secret_key = _site.config.get('COIL_SECRET_KEY')
    app.config['COIL_URL'] = _site.config.get('COIL_URL')
    app.config['REDIS_URL'] = _site.config.get('COIL_REDIS_URL',
                                               'redis://localhost:6379/0')
    db = redis.StrictRedis.from_url(app.config['REDIS_URL'])
    q = rq.Queue(connection=db)

    _site.template_hooks['menu'].append(generate_menu)
    _site.template_hooks['menu_alt'].append(generate_menu_alt)

    app.config['NIKOLA_URL'] = _site.config['SITE_URL']
    _site.config['NAVIGATION_LINKS'] = {
        'en': (
            (app.config['NIKOLA_URL'],
             '<i class="fa fa-globe"></i> Back to website'),
            ('http://coil.readthedocs.org/en/latest/user/',
             '<i class="fa fa-question-circle"></i> Coil CMS Help'),
        )
    }
    _site.GLOBAL_CONTEXT['navigation_links'] = _site.config['NAVIGATION_LINKS']
    TITLE = _site.GLOBAL_CONTEXT['blog_title']('en') + ' Administration'
    _site.config['BLOG_TITLE'] = TranslatableSetting(
        'BLOG_TITLE', TITLE, _site.config['TRANSLATIONS'])
    _site.GLOBAL_CONTEXT['blog_title'] = _site.config['BLOG_TITLE']
    _site.GLOBAL_CONTEXT['lang'] = 'en'
    _site.GLOBAL_CONTEXT['extra_head_data'] = TranslatableSetting(
        'EXTRA_HEAD_DATA',
        """<link href="//maxcdn.bootstrapcdn.com/font-awesome/4.2.0/css/"""
        """font-awesome.min.css" rel="stylesheet">\n"""
        """<link href="/coil_assets/css/coil.css" rel="stylesheet">""",
        _site.config['TRANSLATIONS'])
    # HACK: body_end appears after extra_js from templates, so we must use
    #       social_buttons_code instead
    _site.GLOBAL_CONTEXT['social_buttons_code'] = TranslatableSetting(
        'SOCIAL_BUTTONS_CODE',
        """<script src="/coil_assets/js/coil.js"></script>""",
        _site.config['TRANSLATIONS'])

    # Theme must inherit from bootstrap3, because we have hardcoded HTML.
    bs3 = (('bootstrap3' in _site.THEMES)
           or ('bootstrap3-jinja' in _site.THEMES))
    if not bs3:
        app.logger.notice("THEME does not inherit from 'bootstrap3' or "
                          "'bootstrap3-jinja', using 'bootstrap3' instead.")
        _site.config['THEME'] = 'bootstrap3'
        # Reloading some things
        _site._THEMES = None
        _site._get_themes()
        _site._template_system = None
        _site._get_template_system()
        if 'has_custom_css' in _site._GLOBAL_CONTEXT:
            del _site._GLOBAL_CONTEXT['has_custom_css']
        _site._get_global_context()

    tmpl_dir = pkg_resources.resource_filename(
        'coil', os.path.join('data', 'templates', _site.template_system.name))
    if os.path.isdir(tmpl_dir):
        # Inject tmpl_dir low in the theme chain
        _site.template_system.inject_directory(tmpl_dir)

    # Site proxy
    site = SiteProxy(db, _site, app.logger)
    configure_url(app.config['COIL_URL'])


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


def generate_menu():
    """Generate ``menu`` with the rebuild link.

    :return: HTML fragment
    :rtype: str
    """
    if db.get('site:needs_rebuild') not in ('0', '-1'):
        return ('</li><li><a href="/rebuild"><i class="fa fa-fw '
                'fa-warning"></i> <strong>Rebuild</strong></a></li>')
    else:
        return ('</li><li><a href="/rebuild"><i class="fa fa-fw '
                'fa-cog"></i> Rebuild</a></li>')


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

    return _site.render_template(template_name, None, context), code, headers


def error(desc, code, permalink):
    """Render an error page.

    :param str desc: Error description
    :param int code: HTTP status code
    :param str permalink: Path to page generating errors
    :return: HTML fragment (from :func:`render`)
    :rtype: str
    """
    return render('coil_error.tmpl',
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


app = Flask('coil')


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


class User(object):
    """An user.  Compatible with Flask-Login."""
    def __init__(self, uid, username, realname, password, email, active,
                 is_admin, can_edit_all_posts, wants_all_posts,
                 can_upload_attachments, can_rebuild_site,
                 can_transfer_post_authorship):
        """Initialize an user with specified settings."""
        self.uid = int(uid)
        self.username = username
        self.realname = realname
        self.password = password
        self.email = email
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
    d = db.hgetall('user:{0}'.format(uid))
    if d:
        for p in PERMISSIONS:
            d[p] = d[p] == '1'
        return User(uid=uid, **d)
    else:
        return None


def find_user_by_name(username):
    """Get an user by their username.

    :param str username: Username to find
    :return: the user
    :rtype: User object or None
    """
    uid = db.hget('users', username)
    if uid:
        return get_user(uid)
    else:
        return None


def write_user(user):
    """Write an user ot the database.

    :param User user: User to write
    """

    udata = {}

    for f in USER_FIELDS:
        udata[f] = getattr(user, f)

    for p in PERMISSIONS:
        udata[p] = '1' if getattr(user, p) else '0'
    db.hmset('user:{0}'.format(user.uid), udata)


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
    form = LoginForm()
    if request.method == 'POST':
        if form.validate():
            user = find_user_by_name(request.form['username'])
            if not user:
                alert = 'Invalid credentials.'
                code = 401
            else:
                if check_password(user.password,
                                  request.form['password']) and user.is_active:
                    login_user(user, remember=('remember' in request.form))
                    return redirect('/')
                else:
                    alert = "Invalid credentials."
                    code = 401
        else:
            alert = 'Invalid credentials.'
            code = 401
    else:
        if request.args.get('status') == 'unauthorized':
            alert = 'Please log in to access this page.'
        elif request.args.get('status') == 'logout':
            alert = 'Logged out successfully.'
            alert_status = 'success'
    return render('coil_login.tmpl', {'title': 'Login', 'permalink': '/login',
                                       'alert': alert, 'form': form,
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
    context = {'postform': NewPostForm(),
               'pageform': NewPageForm(),
               'delform': DeleteForm()}

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
        posts = site.all_posts
        pages = site.pages
    else:
        wants = False
        posts = []
        pages = []
        for p in site.timeline:
            if (p.meta('author.uid')
                    and p.meta('author.uid') != str(current_user.uid)):
                continue
            if p.is_post:
                posts.append(p)
            else:
                pages.append(p)

    context['posts'] = posts
    context['pages'] = pages
    context['title'] = 'Posts & Pages'
    context['permalink'] = '/'
    context['wants'] = wants
    return render('coil_index.tmpl', context)


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

    current_auid = int(post.meta('author.uid') or current_user.uid)

    if (not current_user.can_edit_all_posts
            and current_auid != current_user.uid):
        return error("Cannot edit posts of other users.", 401,
                     '/edit/' + path)

    if request.method == 'POST':
        meta = {}
        for k, v in request.form.items():
            meta[k] = v
        meta.pop('_wysihtml5_mode', '')
        try:
            meta['author'] = get_user(meta['author.uid']).realname
            author_change_success = True
        except:
            author_change_success = False
        if (not current_user.can_transfer_post_authorship
                or not author_change_success):
            meta['author'] = post.meta('author') or current_user.realname
            meta['author.uid'] = str(current_auid)

        twofile = post.is_two_file
        onefile = not twofile
        post.compiler.create_post(post.source_path, onefile=onefile,
                                  is_page=False, **meta)

        context['post_content'] = meta['content']

        if twofile:
            meta_path = os.path.splitext(path)[0] + '.meta'
            # We cannot save `content` as meta, otherwise things break badly
            meta.pop('content', '')
            with io.open(meta_path, 'w+', encoding='utf-8') as fh:
                fh.write(write_metadata(meta))
        scan_site()
        db.set('site:needs_rebuild', '1')
        post = find_post(path)
        context['action'] = 'save'
    else:
        context['action'] = 'edit'
        with io.open(path, 'r', encoding='utf-8') as fh:
            context['post_content'] = fh.read()
            if not post.is_two_file:
                context['post_content'] = context['post_content'].split(
                    '\n\n', 1)[1]

    context['post'] = post
    users = []
    last_uid = int(db.get('last_uid'))
    for u in range(1, last_uid + 1):
        realname, active = db.hmget('user:{0}'.format(u), 'realname', 'active')
        if active == '1':
            users.append((u, realname))
    context['users'] = sorted(users)
    context['current_auid'] = current_auid
    context['title'] = 'Editing {0}'.format(post.title())
    context['permalink'] = '/edit/' + path
    context['is_html'] = post.compiler.name == 'html'
    return render('coil_post_edit.tmpl', context)


@app.route('/delete', methods=['POST'])
@login_required
def delete():
    """Delete a post."""
    form = DeleteForm()
    path = request.form['path']
    post = find_post(path)
    if post is None:
        return error("No such post or page.", 404, '/delete')
    if not form.validate():
        return error("Bad Request", 400, '/delete')

    current_auid = int(post.meta('author.uid') or current_user.uid)

    if (not current_user.can_edit_all_posts
            and current_auid != current_user.uid):
        return error("Cannot edit posts of other users.", 401, '/delete')

    os.unlink(path)
    if post.is_two_file:
        meta_path = os.path.splitext(path)[0] + '.meta'
        os.unlink(meta_path)
    scan_site()
    db.set('site:needs_rebuild', '1')
    return redirect('/')


@app.route('/api/rebuild')
@login_required
def api_rebuild():
    """Rebuild the site (internally)."""
    build_job = q.fetch_job('build')
    orphans_job = q.fetch_job('orphans')

    if not build_job and not orphans_job:
        build_job = q.enqueue_call(func=coil.tasks.build,
                                   args=(app.config['REDIS_URL'],
                                         app.config['NIKOLA_ROOT']),
                                   job_id='build')
        orphans_job = q.enqueue_call(func=coil.tasks.orphans,
                                     args=(app.config['REDIS_URL'],
                                           app.config['NIKOLA_ROOT']),
                                     job_id='orphans', depends_on=build_job)

    d = json.dumps({'build': build_job.meta, 'orphans': orphans_job.meta})

    if ('status' in build_job.meta and
            build_job.meta['status'] is not None
            and 'status' in orphans_job.meta and
            orphans_job.meta['status'] is not None):
        rq.cancel_job('build', db)
        rq.cancel_job('orphans', db)
        db.set('site:needs_rebuild', '0')

    return d


@app.route('/rebuild')
@login_required
def rebuild():
    """Rebuild the site with a nice UI."""
    scan_site()  # for good measure
    if not current_user.can_rebuild_site:
        return error('You are not permitted to rebuild the site.</p>'
                     '<p class="lead">Contact an administartor for '
                     'more information.', 401, '/rebuild')
    db.set('site:needs_rebuild', '-1')
    if not q.fetch_job('build') and not q.fetch_job('orphans'):
        b = q.enqueue_call(func=coil.tasks.build,
                           args=(app.config['REDIS_URL'],
                                 app.config['NIKOLA_ROOT']), job_id='build')
        q.enqueue_call(func=coil.tasks.orphans,
                       args=(app.config['REDIS_URL'],
                             app.config['NIKOLA_ROOT']), job_id='orphans',
                       depends_on=b)

    return render('coil_rebuild.tmpl',
                  {'title': 'Rebuild', 'permalink': '/rebuild'})


@app.route('/bower_components/<path:path>')
def serve_bower_components(path):
    """Serve bower components.

    This is meant to be used ONLY by the internal dev server.
    Please configure your web server to handle requests to this URL::

        /bower_components/ => coil/data/bower_components
    """
    res = pkg_resources.resource_filename(
        'coil', os.path.join('data', 'bower_components'))
    return send_from_directory(res, path)


@app.route('/coil_assets/<path:path>')
def serve_coil_assets(path):
    """Serve Coil assets.

    This is meant to be used ONLY by the internal dev server.
    Please configure your web server to handle requests to this URL::

        /coil_assets/ => coil/data/coil_assets
    """
    res = pkg_resources.resource_filename(
        'coil', os.path.join('data', 'coil_assets'))
    return send_from_directory(res, path)


@app.route('/assets/<path:path>')
def serve_assets(path):
    """Serve Nikola assets.

    This is meant to be used ONLY by the internal dev server.
    Please configure your web server to handle requests to this URL::

        /assets/ => output/assets
    """
    res = os.path.join(app.config['NIKOLA_ROOT'],
                       _site.config["OUTPUT_FOLDER"], 'assets')
    return send_from_directory(res, path)


@app.route('/new/<obj>', methods=['POST'])
@login_required
def new(obj):
    """Create a new post or page.

    :param str obj: Object to create (post or page)
    """
    title = request.form['title']
    _site.config['ADDITIONAL_METADATA']['author.uid'] = current_user.uid
    try:
        title = title.encode(sys.stdin.encoding)
    except (AttributeError, TypeError):
        title = title.encode('utf-8')
    try:
        if obj == 'post':
            f = NewPostForm()
            if f.validate():
                _site.commands.new_post(title=title,
                                        author=current_user.realname,
                                        content_format='html')
            else:
                return error("Bad Request", 400, '/new/' + obj)
        elif obj == 'page':
            f = NewPageForm()
            if f.validate():
                _site.commands.new_page(title=title,
                                        author=current_user.realname,
                                        content_format='html')
            else:
                return error("Bad Request", 400, '/new/' + obj)
        else:
            return error("Cannot create {0} — unknown type.".format(obj),
                         400, '/new/' + obj)
    except SystemExit:
        return error("This {0} already exists!".format(obj),
                     500, '/new/' + obj)
    finally:
        del _site.config['ADDITIONAL_METADATA']['author.uid']
    # reload post list and go to index
    scan_site()
    db.set('site:needs_rebuild', '1')
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
    form = AccountForm()
    if request.method == 'POST':
        if not form.validate():
            return error("Bad Request", 400, "/account")
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
        current_user.email = data['email']
        current_user.wants_all_posts = 'wants_all_posts' in data
        write_user(current_user)

    return render('coil_account.tmpl',
                  context={'title': 'My account',
                           'permalink': '/account',
                           'action': action,
                           'alert': alert,
                           'alert_status': alert_status,
                           'form': form})


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
        last_uid = int(db.get('last_uid'))
        USERS = {i: get_user(i) for i in range(1, last_uid + 1)}
        return render('coil_users.tmpl',
                      context={'title': 'Users',
                               'permalink': '/users',
                               'USERS': USERS,
                               'alert': alert,
                               'alert_status': alert_status,
                               'delform': UserDeleteForm(),
                               'editform': UserEditForm()})


@app.route('/users/edit', methods=['POST'])
@login_required
def acp_users_edit():
    """Edit an user account."""
    global current_user

    if not current_user.is_admin:
        return error("Not authorized to edit users.", 401, "/users/edit")
    data = request.form

    form = UserEditForm()
    if not form.validate():
        return error("Bad Request", 400, "/users/edit")
    action = data['action']

    if action == 'new':
        if not data['username']:
            return error("No username to create specified.", 400,
                         "/users/edit")
        uid = db.incr('last_uid')
        pf = [False for p in PERMISSIONS]
        pf[0] = True  # active
        user = User(uid, data['username'], '', '', *pf)
        write_user(user)
        db.hset('users', user.username, user.uid)
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

        if data['username'] != user.username:
            db.hdel('users', user.username)
            user.username = data['username']
            db.hset('users', user.username, user.uid)
        user.realname = data['realname']
        user.email = data['email']
        for p in PERMISSIONS:
            setattr(user, p, p in data)
        user.active = True
        if user.uid == current_user.uid:
            user.is_admin = True
            current_user = user
        write_user(user)

    return render('coil_users_edit.tmpl',
                  context={'title': 'Edit user',
                           'permalink': '/users/edit',
                           'user': user,
                           'new': new,
                           'action': action,
                           'alert': alert,
                           'alert_status': alert_status,
                           'form': form})


@app.route('/users/delete', methods=['POST'])
@login_required
def acp_users_delete():
    """Delete or undelete an user account."""
    if not current_user.is_admin:
        return error("Not authorized to edit users.", 401, "/users/delete")
    form = UserDeleteForm()
    if not form.validate():
        return error("Bad Request", 400, '/users/delete')
    user = get_user(int(request.form['uid']))
    direction = request.form['direction']
    if not user:
        return error("User does not exist.", 404, "/users/delete")
    else:
        for p in PERMISSIONS:
            setattr(user, p, False)
        user.active = direction == 'undel'
        write_user(user)
        return redirect('/users?status={_del}eted'.format(_del=direction))


@app.route('/users/permissions', methods=['GET', 'POST'])
@login_required
def acp_users_permissions():
    """Change user permissions."""
    if not current_user.is_admin:
        return error("Not authorized to edit users.",
                     401, "/users/permissions")

    form = PermissionsForm()
    users = {}
    last_uid = int(db.get('last_uid'))
    if request.method == 'POST':
        if not form.validate():
            return error("Bad Request", 400, '/users/permissions')
        for uid in range(1, last_uid + 1):
            user = get_user(uid)
            for perm in PERMISSIONS:
                if '{0}.{1}'.format(uid, perm) in request.form:
                    setattr(user, perm, True)
                else:
                    setattr(user, perm, False)
            if uid == current_user.uid:
                user.is_admin = True  # cannot deadmin oneself
                user.active = True  # cannot deactivate oneself
            write_user(user)
            users[uid] = user
        action = 'save'
    else:
        action = 'edit'

    def display_permission(user, permission):
        """Display a permission."""
        checked = 'checked' if getattr(user, permission) else ''
        if permission == 'wants_all_posts' and not user.can_edit_all_posts:
            # If this happens, permissions are damaged.
            checked = ''
        if user.uid == current_user.uid and permission in ['active',
                                                           'is_admin']:
            disabled = 'disabled'
        else:
            disabled = ''
        permission_a = permission
        if permission == 'active':
            permission_a = 'is_active'
        d = ('<input type="checkbox" name="{0}.{1}" data-uid="{0}" '
             'data-perm="{4}" class="u{0}" {2} {3}>')
        return d.format(user.uid, permission, checked, disabled, permission_a)

    for uid in range(1, last_uid + 1):
        users[uid] = get_user(uid)

    return render('coil_users_permissions.tmpl',
                  context={'title': 'Permissions',
                           'permalink': '/users/permissions',
                           'USERS': users,
                           'PERMISSIONS': PERMISSIONS,
                           'action': action,
                           'json': json,
                           'form': form,
                           'display_permission': display_permission})

if not os.path.exists('._COIL_NO_CONFIG') and os.path.exists('conf.py'):
    configure_site()
else:
    # no Nikola site available
    app = None
