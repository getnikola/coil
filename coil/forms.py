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

from flask.ext.wtf import Form
from wtforms.fields import TextField, PasswordField, FileField, BooleanField
from wtforms.validators import Required, ValidationError


class LoginForm(Form):
    """A login form."""
    username = TextField('Username', validators=[Required()])
    password = PasswordField('Password', validators=[Required()])
    remember = BooleanField('Remember me')


class NewPostForm(Form):
    """A new post form."""
    title = TextField('Title', validators=[Required()])


class NewPageForm(Form):
    """A new page form."""
    title = TextField('Title', validators=[Required()])


class DeleteForm(Form):
    """A deletion form.  Strong Bad sold separately."""
    path = TextField('Path', validators=[Required()])


class UserDeleteForm(Form):
    """An user deletion form."""
    direction = TextField('Direction', validators=[Required()])
    uid = TextField('UID', validators=[Required()])

    def validate_direction(form, field):
        if field.data not in ['del', 'undel']:
            raise ValidationError('invalid direction')


class AccountForm(Form):
    """An account form, used for CSRF protection only."""
    pass


class UserImportForm(Form):
    """A user import form."""
    tsv = FileField("TSV File")


class UserEditForm(Form):
    """A user editor form, used for CSRF protection only."""
    pass


class PermissionsForm(Form):
    """A permissions form, used for CSRF protection only."""
    pass


class PwdHashForm(Form):
    """A password hash form."""
    newpwd1 = TextField('New password', validators=[Required()])
    newpwd2 = TextField('Repeat new password', validators=[Required()])
