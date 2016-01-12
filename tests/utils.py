"""
Testing utils
-------------
"""

from contextlib import contextmanager
from datetime import datetime, timedelta
import json

from flask import Response
from flask.testing import FlaskClient
from werkzeug.utils import cached_property


class AutoAuthFlaskClient(FlaskClient):
    """
    A helper FlaskClient class with a useful for testing ``login`` context
    manager.
    """

    def __init__(self, *args, **kwargs):
        super(AutoAuthFlaskClient, self).__init__(*args, **kwargs)
        self._user = None
        self._auth_scopes = None

    @contextmanager
    def login(self, user, auth_scopes=None):
        """
        Example:
            >>> with flask_app_client.login(user, auth_scopes=['users:read']):
            ...     flask_app_client.get('/api/v1/users/')
        """
        self._user = user
        self._auth_scopes = auth_scopes or []
        yield self
        self._user = None
        self._auth_scopes = None

    def open(self, *args, **kwargs):
        if self._user is not None:
            from app.extensions import db
            from app.modules.auth.models import OAuth2Token

            oauth2_bearer_token = OAuth2Token(
                client_id=0,
                user=self._user,
                token_type='Bearer',
                access_token='test_access_token',
                _scopes=' '.join(self._auth_scopes),
                expires=datetime.utcnow() + timedelta(days=1),
            )

            # pylint: disable=no-member
            db.session.add(oauth2_bearer_token)
            db.session.commit()

            extra_headers = (
                (
                    'Authorization',
                    '{token.token_type} {token.access_token}'.format(token=oauth2_bearer_token)
                ),
            )
            if kwargs.get('headers'):
                kwargs['headers'] += extra_headers
            else:
                kwargs['headers'] = extra_headers

        response = super(AutoAuthFlaskClient, self).open(*args, **kwargs)

        if self._user is not None:
            # pylint: disable=no-member
            db.session.delete(oauth2_bearer_token)
            db.session.commit()

        return response


class JSONResponse(Response):
    # pylint: disable=too-many-ancestors
    """
    A Response class with extra useful helpers, i.e. ``.json`` property.
    """

    @cached_property
    def json(self):
        return json.loads(self.get_data(as_text=True))


def generate_user_instance(
        user_id=None,
        username="username",
        password=None,
        email=None,
        first_name="First Name",
        middle_name="Middle Name",
        last_name="Last Name",
        created=None,
        updated=None,
        is_active=True,
        is_readonly=False,
        is_admin=False
):
    """
    Returns:
        user_instance (User) - an not committed to DB instance of a User model.
    """
    # pylint: disable=too-many-arguments
    from app.modules.users.models import User
    if password is None:
        password = '%s_password' % username
    user_instance = User(
        id=user_id,
        username=username,
        first_name=first_name,
        middle_name=middle_name,
        last_name=last_name,
        password=password,
        email=email or '%s@email.com' % username,
        created=created or datetime.now(),
        updated=updated or datetime.now(),
        is_active=is_active,
        is_readonly=is_readonly,
        is_admin=is_admin,
    )
    user_instance.password_secret = password
    return user_instance
