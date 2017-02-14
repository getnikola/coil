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
import operator
import requests
import coil.tasks
from nikola.utils import (unicode_str, get_logger, ColorfulStderrHandler,
                          write_metadata, TranslatableSetting)
import nikola.plugins.command.new_post
from flask import (Flask, request, redirect, send_from_directory, g, session,
                   url_for)
from flask.ext.login import (LoginManager, login_required, login_user,
                             logout_user, current_user, make_secure_token)
from passlib.hash import bcrypt_sha256
from coil.utils import USER_FIELDS, PERMISSIONS, PERMISSIONS_E, SiteProxy
from coil.forms import (LoginForm, NewPostForm, NewPageForm, DeleteForm,
                        UserDeleteForm, UserEditForm, AccountForm,
                        PermissionsForm, UserImportForm, PwdHashForm)

_site = None
site = None
app = None
db = None
q = None


def scan_site():
    """Rescan the site."""
    site.scan_posts(really=True, ignore_quit=False, quiet=True)


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
    _site = _dn.nikola
    _site.init_plugins()
    _dn.sub_cmds = _dn.get_cmds()
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
    app.config['COIL_LOGIN_CAPTCHA'] = _site.config.get(
        'COIL_LOGIN_CAPTCHA',
        {'enabled': False, 'site_key': '', 'secret_key': ''})
    app.config['COIL_USERS_PREVENT_EDITING'] = _site.config.get('COIL_USERS_PREVENT_EDITING', [])
    app.config['COIL_LIMITED'] = _site.config.get('COIL_LIMITED', False)
    app.config['REDIS_URL'] = _site.config.get('COIL_REDIS_URL',
                                               'redis://localhost:6379/0')
    if app.config['COIL_LIMITED']:
        app.config['COIL_USERS'] = _site.config.get('COIL_USERS', {})
        _site.coil_needs_rebuild = '0'
    else:
        db = redis.StrictRedis.from_url(app.config['REDIS_URL'])
        q = rq.Queue(name='coil', connection=db)

    _site.template_hooks['menu'].append(generate_menu)
    _site.template_hooks['menu_alt'].append(generate_menu_alt)

    app.config['NIKOLA_URL'] = _site.config['SITE_URL']
    _site.config['NAVIGATION_LINKS'] = {
        _site.default_lang: (
            (app.config['NIKOLA_URL'],
             '<i class="fa fa-globe"></i> View Site'),
            ('http://coil.readthedocs.io/user/',
             '<i class="fa fa-question-circle"></i> Help'),
        )
    }
    _site.GLOBAL_CONTEXT['navigation_links'] = _site.config['NAVIGATION_LINKS']
    TITLE = _site.GLOBAL_CONTEXT['blog_title']() + ' Administration'
    _site.config['BLOG_TITLE'] = TranslatableSetting(
        'BLOG_TITLE', TITLE, _site.config['TRANSLATIONS'])
    _site.GLOBAL_CONTEXT['blog_title'] = _site.config['BLOG_TITLE']
    _site.GLOBAL_CONTEXT['lang'] = _site.default_lang
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
    bs3 = (('bootstrap3' in _site.THEMES) or
           ('bootstrap3-jinja' in _site.THEMES))
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

    # Commands proxy (only for Nikola commands)
    _site.commands = nikola.utils.Commands(
        _site.doit,
        None,
        {'cmds': _site._commands}
    )

    # Site proxy
    if app.config['COIL_LIMITED']:
        site = _site
        scan_site()
    else:
        site = SiteProxy(db, _site, app.logger)

    configure_url(app.config['COIL_URL'])


def password_hash(password):
    """Hash the password, using bcrypt+sha256.

    .. versionchanged:: 1.1.0

    :param str password: Password in plaintext
    :return: password hash
    :rtype: str
    """
    try:
        return bcrypt_sha256.encrypt(password)
    except TypeError:
        return bcrypt_sha256.encrypt(password.decode('utf-8'))


def check_password(pwdhash, password):
    """Check the password hash from :func:`password_hash`.

    .. versionchanged:: 1.1.0

    :param str pwdhash: Hash from :func:`password_hash` to check
    :param str password: Password in plaintext
    :return: password match
    :rtype: bool
    """
    return bcrypt_sha256.verify(password, pwdhash)


def check_old_password(pwdhash, password):
    """Check the old password hash from :func:`password_hash`.

    .. versionadded:: 1.1.0

    :param str pwdhash: Hash from :func:`password_hash` to check
    :param str password: Password in plaintext
    :return: password match
    :rtype: bool
    """
    from flask.ext.bcrypt import Bcrypt
    app.config['BCRYPT_LOG_ROUNDS'] = 12
    bcrypt = Bcrypt(app)
    return bcrypt.check_password_hash(pwdhash, password)


def generate_menu():
    """Generate ``menu`` with the rebuild link.

    :return: HTML fragment
    :rtype: str
    """
    if db is not None:
        needs_rebuild = db.get('site:needs_rebuild')
    else:
        needs_rebuild = site.coil_needs_rebuild
    if needs_rebuild not in (u'0', u'-1', b'0', b'-1'):
        return ('</li><li><a href="{0}"><i class="fa fa-fw '
                'fa-warning"></i> <strong>Rebuild</strong></a></li>'.format(
                    url_for('rebuild')))
    else:
        return ('</li><li><a href="{0}"><i class="fa fa-fw '
                'fa-cog"></i> Rebuild</a></li>'.format(url_for('rebuild')))


def generate_menu_alt():
    """Generate ``menu_alt`` with log in/out links.

    :return: HTML fragment
    :rtype: str
    """
    if not current_user.is_authenticated():
        return ('<li><a href="{0}"><i class="fa fa-fw fa-sign-in"></i> '
                'Log in</a></li>'.format(url_for('login')))
    if db is not None and current_user.is_admin:
        edit_entry = (
            '<li><a href="{0}"><i class="fa fa-fw fa-users"></i> '
            'Manage users</a></li>'
            '<li><a href="{1}"><i class="fa fa-fw fa-cubes"></i> '
            'Permissions</a></li>'.format(
                url_for('acp_users'), url_for('acp_users_permissions')))
    else:
        edit_entry = ''
    return """
    <li class="dropdown">
        <a href="#" class="dropdown-toggle" data-toggle="dropdown"
            role="button" aria-expanded="false">
            <i class="fa fa-fw fa-user"></i>
            {0} [{1}] <span class="caret"></span></a>
        <ul class="dropdown-menu" role="menu">
            <li><a href="{3}"><i class="fa fa-fw fa-sliders"></i>
            Account</a></li>
            {2}
            <li><a href="{4}"><i class="fa fa-fw fa-sign-out"></i>
            Log out</a></li>
        </ul>
    </li>""".format(current_user.realname, current_user.username, edit_entry,
                    url_for('acp_account'), url_for('logout'))


def _author_get(post):
    """Get the name of the post author.

    :param Post post: The post object to determine authorship of
    :return: Author real name
    :rtype: str
    """
    a = post.meta('author')
    return a if a else current_user.realname


def _author_uid_get(post):
    """Get the UID of the post author.

    :param Post post: The post object to determine authorship of
    :return: Author UID
    :rtype: str
    """
    u = post.meta('author.uid')
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
    if app.config['COIL_URL'].startswith('https') and not request.url.startswith('https'):
        # patch request URL for HTTPS proxy (eg. CloudFlare)
        context['permalink'] = request.url.replace('http', 'https', 1)
    else:
        context['permalink'] = request.url
    context['url_for'] = url_for
    headers['Pragma'] = 'no-cache'
    headers['Cache-Control'] = 'private, max-age=0, no-cache'

    try:
        mcp = current_user.must_change_password in (True, '1')
    except AttributeError:
        mcp = False

    if mcp and not context.get('pwdchange_skip', False):
        return redirect(url_for('acp_account') + '?status=pwdchange')

    return _site.render_template(template_name, None, context), code, headers


def error(desc, code):
    """Render an error page.

    :param str desc: Error description
    :param int code: HTTP status code
    :return: HTML fragment (from :func:`render`)
    :rtype: str
    """
    return render('coil_error.tmpl',
                  {'title': 'Error',
                   'code': code,
                   'desc': desc},
                  code)


def _unauthorized():
    """Redirect to the “unauthorized” page."""
    return redirect(url_for('login') + '?status=unauthorized')


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

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.unauthorized_callback = _unauthorized


class User(object):
    """An user.  Compatible with Flask-Login."""
    def __init__(self, uid, username, realname, password, email, active,
                 is_admin, can_edit_all_posts, wants_all_posts,
                 can_upload_attachments, can_rebuild_site,
                 can_transfer_post_authorship, must_change_password):
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
        self.must_change_password = must_change_password

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
    if db is not None:
        try:
            uid = uid.decode('utf-8')
        except AttributeError:
            pass
        d = db.hgetall('user:{0}'.format(uid))
        if d:
            nd = {}
            # strings everywhere
            for k in d:
                try:
                    nd[k.decode('utf-8')] = d[k].decode('utf-8')
                except AttributeError:
                    try:
                        nd[k.decode('utf-8')] = d[k]
                    except AttributeError:
                        nd[k] = d[k]
            for p in PERMISSIONS:
                nd[p] = nd.get(p) == '1'
            return User(uid=uid, **nd)
        else:
            return None
    else:
        d = app.config['COIL_USERS'].get(uid)
        if d:
            return User(uid=uid, **d)
        else:
            return None


def find_user_by_name(username):
    """Get an user by their username.

    :param str username: Username to find
    :return: the user
    :rtype: User object or None
    """
    if db is not None:
        uid = db.hget('users', username)
        if uid:
            return get_user(uid)
    else:
        for uid, u in app.config['COIL_USERS'].items():
            if u['username'] == username:
                return get_user(uid)


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


@app.route('/login/', methods=['GET', 'POST'])
def login():
    """Handle user authentication.

    If requested over GET, present login page.
    If requested over POST, log user in.

    :param str status: Status of previous request/login attempt
    """
    alert = None
    alert_status = 'danger'
    code = 200
    captcha = app.config['COIL_LOGIN_CAPTCHA']
    form = LoginForm()
    if request.method == 'POST':
        if form.validate():
            user = find_user_by_name(request.form['username'])
            if not user:
                alert = 'Invalid credentials.'
                code = 401
            if captcha['enabled']:
                r = requests.post('https://www.google.com/recaptcha/api/siteverify',
                                  data={'secret': captcha['secret_key'],
                                        'response': request.form['g-recaptcha-response'],
                                        'remoteip': request.remote_addr})
                if r.status_code != 200:
                    alert = 'Cannot check CAPTCHA response.'
                    code = 500
                else:
                    rj = r.json()
                    if not rj['success']:
                        alert = 'Invalid CAPTCHA response. Please try again.'
                        code = 401
            if code == 200:
                try:
                    pwd_ok = check_password(user.password,
                                            request.form['password'])
                except ValueError:
                    if user.password.startswith('$2a$12'):
                        # old bcrypt hash
                        pwd_ok = check_old_password(user.password,
                                                    request.form['password'])
                        if pwd_ok:
                            user.password = password_hash(
                                request.form['password'])
                            write_user(user)
                    else:
                        pwd_ok = False

                if pwd_ok and user.is_active:
                    login_user(user, remember=('remember' in request.form))
                    return redirect(url_for('index'))
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
    return render('coil_login.tmpl', {'title': 'Login', 'alert': alert, 'form':
                                      form, 'alert_status': alert_status,
                                      'pwdchange_skip': True,
                                      'captcha': captcha},
                  code)


@app.route('/logout/')
@login_required
def logout():
    """Log the user out and redirect them to the login page."""
    logout_user()
    return redirect(url_for('login') + '?status=logout')


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
            if (p.meta('author.uid') and
                    p.meta('author.uid') != str(current_user.uid)):
                continue
            if p.is_post:
                posts.append(p)
            else:
                pages.append(p)

    context['posts'] = posts
    context['pages'] = pages
    context['title'] = 'Posts & Pages'
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
        return error("No such post or page.", 404)

    current_auid = int(post.meta('author.uid') or current_user.uid)

    if (not current_user.can_edit_all_posts and
            current_auid != current_user.uid):
        return error("Cannot edit posts of other users.", 401)

    if request.method == 'POST':
        meta = {}
        for k, v in request.form.items():
            meta[k] = v
        meta.pop('_wysihtml5_mode', '')
        try:
            meta['author'] = get_user(meta['author.uid']).realname
            current_auid = int(meta['author.uid'])
            author_change_success = True
        except Exception:
            author_change_success = False
        if (not current_user.can_transfer_post_authorship or
                not author_change_success):
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
        if db is not None:
            db.set('site:needs_rebuild', '1')
        else:
            site.coil_needs_rebuild = '1'
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
    if db is not None:
        uids = db.hgetall('users').values()
        for u in uids:
            u = u.decode('utf-8')
            realname, active = db.hmget('user:{0}'.format(u),
                                        'realname', 'active')
            if active in (u'1', b'1'):
                users.append((u, realname.decode('utf-8')))
    else:
        for u, d in app.config['COIL_USERS'].items():
            if d['active']:
                users.append((int(u), d['realname']))
    context['users'] = sorted(users)
    context['current_auid'] = current_auid
    context['title'] = 'Editing {0}'.format(post.title())
    context['is_html'] = post.compiler.name == 'html'
    return render('coil_post_edit.tmpl', context)


@app.route('/delete/', methods=['POST'])
@login_required
def delete():
    """Delete a post."""
    form = DeleteForm()
    path = request.form['path']
    post = find_post(path)
    if post is None:
        return error("No such post or page.", 404)
    if not form.validate():
        return error("Bad Request", 400)

    current_auid = int(post.meta('author.uid') or current_user.uid)

    if (not current_user.can_edit_all_posts and
            current_auid != current_user.uid):
        return error("Cannot edit posts of other users.", 401)

    os.unlink(path)
    if post.is_two_file:
        meta_path = os.path.splitext(path)[0] + '.meta'
        os.unlink(meta_path)
    scan_site()
    if db is not None:
        db.set('site:needs_rebuild', '1')
    else:
        site.coil_needs_rebuild = '1'
    return redirect(url_for('index'))


@app.route('/api/rebuild/')
@login_required
def api_rebuild():
    """Rebuild the site (internally)."""
    if db is None:
        return '{"error": "single-user mode"}'
    build_job = q.fetch_job('build')
    orphans_job = q.fetch_job('orphans')

    if not build_job and not orphans_job:
        build_job = q.enqueue_call(func=coil.tasks.build,
                                   args=(app.config['REDIS_URL'],
                                         app.config['NIKOLA_ROOT'],
                                         ''),
                                   job_id='build')
        orphans_job = q.enqueue_call(func=coil.tasks.orphans,
                                     args=(app.config['REDIS_URL'],
                                           app.config['NIKOLA_ROOT']),
                                     job_id='orphans', depends_on=build_job)

    d = json.dumps({'build': build_job.meta, 'orphans': orphans_job.meta})

    if ('status' in build_job.meta and
            build_job.meta['status'] is not None and
            'status' in orphans_job.meta and
            orphans_job.meta['status'] is not None):
        rq.cancel_job('build', db)
        rq.cancel_job('orphans', db)
        db.set('site:needs_rebuild', '0')
        site.coil_needs_rebuild = '1'

    return d


@app.route('/rebuild/')
@app.route('/rebuild/<mode>/')
@login_required
def rebuild(mode=''):
    """Rebuild the site with a nice UI."""
    scan_site()  # for good measure
    if not current_user.can_rebuild_site:
        return error('You are not permitted to rebuild the site.</p>'
                     '<p class="lead">Contact an administartor for '
                     'more information.', 401)
    if db is not None:
        db.set('site:needs_rebuild', '-1')
        if not q.fetch_job('build') and not q.fetch_job('orphans'):
            b = q.enqueue_call(func=coil.tasks.build,
                               args=(app.config['REDIS_URL'],
                                     app.config['NIKOLA_ROOT'], mode),
                               job_id='build')
            q.enqueue_call(func=coil.tasks.orphans,
                           args=(app.config['REDIS_URL'],
                                 app.config['NIKOLA_ROOT']), job_id='orphans',
                           depends_on=b)
        return render('coil_rebuild.tmpl', {'title': 'Rebuild'})
    else:
        status, outputb = coil.tasks.build_single(mode)
        _, outputo = coil.tasks.orphans_single()
        site.coil_needs_rebuild = '0'
        return render('coil_rebuild_single.tmpl',
                      {'title': 'Rebuild', 'status': '1' if status else '0',
                       'outputb': outputb, 'outputo': outputo})


@app.route('/new/<obj>/', methods=['POST'])
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
                return error("Bad Request", 400)
        elif obj == 'page':
            f = NewPageForm()
            if f.validate():
                _site.commands.new_page(title=title,
                                        author=current_user.realname,
                                        content_format='html')
            else:
                return error("Bad Request", 400)
        else:
            return error("Cannot create {0} — unknown type.".format(obj), 400)
    except SystemExit:
        return error("This {0} already exists!".format(obj), 500)
    finally:
        del _site.config['ADDITIONAL_METADATA']['author.uid']
    # reload post list and go to index
    scan_site()
    if db is not None:
        db.set('site:needs_rebuild', '1')
    else:
        site.coil_needs_rebuild = '1'
    return redirect(url_for('index'))


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


@app.route('/account/', methods=['POST', 'GET'])
@login_required
def acp_account():
    """Manage the user account of currently-logged-in users.

    This does NOT accept admin-specific options.
    """
    if request.args.get('status') == 'pwdchange':
        alert = 'You must change your password before proceeding.'
        alert_status = 'danger'
        pwdchange_skip = True
    else:
        alert = ''
        alert_status = ''
        pwdchange_skip = False

    if db is None:
        form = PwdHashForm()
        return render('coil_account_single.tmpl',
                      context={'title': 'My account',
                               'form': form,
                               'alert': alert,
                               'alert_status': alert_status})

    action = 'edit'
    form = AccountForm()
    if request.method == 'POST':
        if int(current_user.uid) in app.config['COIL_USERS_PREVENT_EDITING']:
            return error("Cannot edit data for this user.", 403)
        if not form.validate():
            return error("Bad Request", 400)
        action = 'save'
        data = request.form
        if data['newpwd1']:
            try:
                pwd_ok = check_password(current_user.password, data['oldpwd'])
            except ValueError:
                if current_user.password.startswith('$2a$12'):
                    # old bcrypt hash
                    pwd_ok = check_old_password(current_user.password,
                                                data['oldpwd'])

            if data['newpwd1'] == data['newpwd2'] and pwd_ok:
                current_user.password = password_hash(data['newpwd1'])
                current_user.must_change_password = False
                pwdchange_skip = True
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
                           'action': action,
                           'alert': alert,
                           'alert_status': alert_status,
                           'form': form,
                           'pwdchange_skip': pwdchange_skip})


@app.route('/account/pwdhash', methods=['POST'])
def acp_pwdhash():
    form = PwdHashForm()
    if not form.validate():
        return error("Bad Request", 400)
    data = request.form
    if data['newpwd1'] == data['newpwd2']:
        pwdhash = password_hash(data['newpwd1'])
        status = True
    else:
        pwdhash = None
        status = False
    return render('coil_pwdhash.tmpl',
                  context={'title': 'My account', 'pwdhash': pwdhash,
                           'status': status, 'form': form})


@app.route('/users/')
@login_required
def acp_users():
    """List all users."""
    if not current_user.is_admin:
        return error("Not authorized to edit users.", 401)
    if not db:
        return error('The ACP is not available in single-user mode.', 500)

    alert = ''
    alert_status = ''
    if request.args.get('status') == 'deleted':
        alert = 'User deleted.'
        alert_status = 'success'
    if request.args.get('status') == 'undeleted':
        alert = 'User undeleted.'
        alert_status = 'success'

    uids = db.hgetall('users').values()
    USERS = sorted([(int(i), get_user(i)) for i in uids], key=operator.itemgetter(0))
    return render('coil_users.tmpl',
                  context={'title': 'Users',
                           'USERS': USERS,
                           'alert': alert,
                           'alert_status': alert_status,
                           'delform': UserDeleteForm(),
                           'editform': UserEditForm(),
                           'importform': UserImportForm()})


@app.route('/users/edit/', methods=['POST'])
@login_required
def acp_users_edit():
    """Edit an user account."""
    global current_user
    if not current_user.is_admin:
        return error("Not authorized to edit users.", 401)
    if not db:
        return error('The ACP is not available in single-user mode.', 500)
    data = request.form

    form = UserEditForm()
    if not form.validate():
        return error("Bad Request", 400)
    action = data['action']

    if action == 'new':
        if not data['username']:
            return error("No username to create specified.", 400)
        uid = max(int(i) for i in db.hgetall('users').values()) + 1
        pf = [False for p in PERMISSIONS]
        pf[0] = True  # active
        pf[7] = True  # must_change_password
        user = User(uid, data['username'], '', '', '', *pf)
        write_user(user)
        db.hset('users', user.username, user.uid)
        new = True
    else:
        user = get_user(data['uid'])
        new = False

    if not user:
        return error("User does not exist.", 404)

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
            user.must_change_password = False
            current_user = user
        write_user(user)

    return render('coil_users_edit.tmpl',
                  context={'title': 'Edit user',
                           'user': user,
                           'new': new,
                           'action': action,
                           'alert': alert,
                           'alert_status': alert_status,
                           'form': form})


@app.route('/users/import/', methods=['POST'])
@login_required
def acp_users_import():
    """Import users from a TSV file."""
    if not current_user.is_admin:
        return error("Not authorized to edit users.", 401)
    if not db:
        return error('The ACP is not available in single-user mode.', 500)

    form = UserImportForm()
    if not form.validate():
        return error("Bad Request", 400)
    fh = request.files['tsv'].stream
    tsv = fh.read()
    return tsv
    # TODO


@app.route('/users/delete/', methods=['POST'])
@login_required
def acp_users_delete():
    """Delete or undelete an user account."""
    if not current_user.is_admin:
        return error("Not authorized to edit users.", 401)
    if not db:
        return error('The ACP is not available in single-user mode.', 500)

    form = UserDeleteForm()
    if not form.validate():
        return error("Bad Request", 400)
    user = get_user(int(request.form['uid']))
    direction = request.form['direction']
    if not user:
        return error("User does not exist.", 404)
    else:
        for p in PERMISSIONS:
            setattr(user, p, False)
        user.active = direction == 'undel'
        write_user(user)
        return redirect(url_for('acp_users') + '?status={_del}eted'.format(
            _del=direction))


@app.route('/users/permissions/', methods=['GET', 'POST'])
@login_required
def acp_users_permissions():
    """Change user permissions."""
    if not current_user.is_admin:
        return error("Not authorized to edit users.", 401)
    if not db:
        return error('The ACP is not available in single-user mode.', 500)

    form = PermissionsForm()
    users = []
    uids = db.hgetall('users').values()
    if request.method == 'POST':
        if not form.validate():
            return error("Bad Request", 400)
        for uid in uids:
            user = get_user(uid)
            for perm in PERMISSIONS:
                if '{0}.{1}'.format(uid, perm) in request.form:
                    setattr(user, perm, True)
                else:
                    setattr(user, perm, False)
            if int(uid) == current_user.uid:
                # Some permissions cannot apply to the current user.
                user.is_admin = True
                user.active = True
                user.must_change_password = False
            write_user(user)
            users.append((uid, user))
        action = 'save'
    else:
        action = 'edit'

    def display_permission(user, permission):
        """Display a permission."""
        checked = 'checked' if getattr(user, permission) else ''
        if permission == 'wants_all_posts' and not user.can_edit_all_posts:
            # If this happens, permissions are damaged.
            checked = ''
        if (user.uid == current_user.uid and permission in [
                'active', 'is_admin', 'must_change_password']):
            disabled = 'disabled'
        else:
            disabled = ''
        permission_a = permission
        if permission == 'active':
            permission_a = 'is_active'
        d = ('<input type="checkbox" name="{0}.{1}" data-uid="{0}" '
             'data-perm="{4}" class="u{0}" {2} {3}>')
        return d.format(user.uid, permission, checked, disabled, permission_a)

    if not users:
        users = [(i, get_user(i)) for i in uids]

    return render('coil_users_permissions.tmpl',
                  context={'title': 'Permissions',
                           'USERS': sorted(users),
                           'UIDS': sorted(uids),
                           'PERMISSIONS_E': PERMISSIONS_E,
                           'action': action,
                           'json': json,
                           'form': form,
                           'display_permission': display_permission})

if not os.path.exists('._COIL_NO_CONFIG') and os.path.exists('conf.py'):
    configure_site()
else:
    # no Nikola site available
    app = None
