from unittest import mock

import pytest
from django.urls import reverse

from ansible_base.authentication.authenticator_plugins.oidc import AuthenticatorPlugin
from ansible_base.authentication.session import SessionAuthentication

authenticated_test_page = "authenticator-list"


@mock.patch("rest_framework.views.APIView.authentication_classes", [SessionAuthentication])
@mock.patch("ansible_base.authentication.authenticator_plugins.oidc.AuthenticatorPlugin.authenticate")
def test_oidc_auth_successful(authenticate, unauthenticated_api_client, oidc_authenticator, user):
    """
    Test that a successful OIDC authentication returns a 200 on the /me endpoint.

    Here we mock the OIDC authentication backend to return a user.
    """
    client = unauthenticated_api_client
    authenticate.return_value = user
    client.login()

    url = reverse(authenticated_test_page)
    response = client.get(url)
    assert response.status_code == 200


@mock.patch("rest_framework.views.APIView.authentication_classes", [SessionAuthentication])
@mock.patch("ansible_base.authentication.authenticator_plugins.oidc.AuthenticatorPlugin.authenticate", return_value=None)
def test_oidc_auth_failed(authenticate, unauthenticated_api_client, oidc_authenticator):
    """
    Test that a failed OIDC authentication returns a 401 on the /me endpoint.
    """
    client = unauthenticated_api_client
    client.login()

    url = reverse(authenticated_test_page)
    response = client.get(url)
    assert response.status_code == 401


@pytest.mark.django_db
@pytest.mark.parametrize(
    "endpoint_url, expected_status_code, expected_error",
    [
        (None, 400, {'OIDC_ENDPOINT': ['This field may not be null.']}),
        ('', 400, {'OIDC_ENDPOINT': ['This field may not be blank.']}),
        ('foobar', 400, {'OIDC_ENDPOINT': ['Enter a valid URL.']}),
        ('123456', 400, {'OIDC_ENDPOINT': ['Enter a valid URL.']}),
        ('/////', 400, {'OIDC_ENDPOINT': ['Enter a valid URL.']}),
        ('...', 400, {'OIDC_ENDPOINT': ['Enter a valid URL.']}),
        ('192.168.1.1', 400, {'OIDC_ENDPOINT': ['Enter a valid URL.']}),
        ('0.0.0.0', 400, {'OIDC_ENDPOINT': ['Enter a valid URL.']}),
        ('httpXX://foobar', 400, {'OIDC_ENDPOINT': ['Enter a valid URL.']}),
        ('http://foobar::not::ip::v6', 400, {'OIDC_ENDPOINT': ["Port could not be cast to integer value as ':not::ip::v6'"]}),
        ('http://foobar:ABDC', 400, {'OIDC_ENDPOINT': ["Port could not be cast to integer value as 'ABDC'"]}),
        ('http://foobar', 201, {}),
        ('http://foobar:80', 201, {}),
        ('https://foobar', 201, {}),
        ('https://foobar:443', 201, {}),
        ('http://[::1]', 201, {}),
        ('http://[::1]:80', 201, {}),
        ('http://[::192.9.5.5]/', 201, {}),
        ('http://[::FFFF:129.144.52.38]:80', 201, {}),
    ],
)
def test_oidc_endpoint_url_validation(
    admin_api_client,
    endpoint_url,
    expected_status_code,
    expected_error,
):
    config = {
        "OIDC_ENDPOINT": endpoint_url,
        "VERIFY_SSL": True,
        "KEY": "12345",
        "SECRET": "abcdefg12345",
    }

    data = {
        "name": "OIDC TEST",
        "enabled": True,
        "create_objects": True,
        "remove_users": True,
        "configuration": config,
        "type": "ansible_base.authentication.authenticator_plugins.oidc",
    }

    url = reverse("authenticator-list")
    response = admin_api_client.post(url, data=data, format="json")
    assert response.status_code == expected_status_code
    if expected_error:
        assert response.json() == expected_error
    else:
        assert response.json()['configuration']['OIDC_ENDPOINT'] == endpoint_url


@mock.patch("social_core.backends.oauth.BaseOAuth2.extra_data")
def test_extra_data(mockedsuper):
    ap = AuthenticatorPlugin()

    class SocialUser:
        def __init__(self):
            self.extra_data = {}

    rDict = {}
    rDict["is_superuser"] = "True"
    rDict["Group"] = ["mygroup"]
    social = SocialUser()
    ap.extra_data(None, None, response=rDict, social=social)
    assert mockedsuper.called
    assert "is_superuser" in social.extra_data
