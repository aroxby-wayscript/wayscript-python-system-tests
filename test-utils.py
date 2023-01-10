from functools import wraps
from pathlib import Path
from time import sleep
from requests.exceptions import HTTPError
import unittest

from wayscript import utils
from wayscript import context


def _dumb_retry(exception_type, exception_filter, max_tries = 10):
    def decorator(f):  # I wanted to do this as a context manager but context managers can't really repeat code
        @wraps(f)
        def _wrapper(*args, **kwargs):
            nonlocal max_tries
            while True:
                try:
                    return f(*args, **kwargs)
                except exception_type as exc:
                    if max_tries > 0 and exception_filter(exc):
                        max_tries -= 1
                        sleep(1)
                    else:
                        raise
        return _wrapper
    return decorator


class TestEnvironment(unittest.TestCase):
    def test_get_all(self):
        token = utils.get_process_execution_user_token()
        process_id = utils.get_process_id()
        refresh = utils.get_refresh_token()
        key = utils.get_application_key()

        self.assertTrue(all([token, process_id, refresh, key]))


class TestClient(unittest.TestCase):
    def setUp(self):
        self.client = utils.WayScriptClient()

    def test__refresh_access_token(self):
        # In order to test using public methods we can do something tricky
        self.client.session.headers.pop('authorization')
        self.client.get_process_detail_expanded(utils.get_process_id())
        self.assertTrue(self.client.session.headers['authorization'])

    def test_get_process_detail_expanded(self):
        process_id = utils.get_process_id()
        response = self.client.get_process_detail_expanded(process_id)
        response.raise_for_status()
        self.assertNotIn('error', response.json())

    def test_get_workspace_integration_detail(self):
        # I can't find any examples of workspace integrations
        response = self.client.get_workspace_integration_detail('')
        self.assertEqual(404, response.status_code)

    def test_get_lair_detail(self):
        lair_id = context.get_lair()['id']
        response = self.client.get_lair_detail(lair_id)
        response.raise_for_status()
        self.assertNotIn('error', response.json())

    def test_get_workspace_detail(self):
        workspace_id = context.get_workspace()['id']
        response = self.client.get_workspace_detail(workspace_id)
        response.raise_for_status()
        self.assertNotIn('error', response.json())

    def test_get_user_detail_by_application_key(self):
        application_key = utils.get_application_key()
        workspace_id = context.get_workspace()['id']
        response = self.client.get_user_detail_by_application_key(application_key, workspace_id)
        response.raise_for_status()
        self.assertNotIn('error', response.json())

    def test_post_webhook_http_trigger_response(self):
        process_id = utils.get_process_id()
        payload = {
            'data': '',
            'headers': {},
            'status_code': 500,
        }
        response = self.client.post_webhook_http_trigger_response(process_id, payload)
        response.raise_for_status()
        self.assertNotIn('error', response.json())

    @_dumb_retry(HTTPError, lambda exception: exception.response.status_code == 404)
    def test_set_lair_secret(self):
        Path('.secrets').touch()
        # To set lair secrets a .secrets file must exist.
        # Sometimes WayScript takes a second to realize we've created this so there's an automatic retry

        lair_id = context.get_lair()['id']
        key = 'password'
        value = 'swordfish'

        response = self.client.set_lair_secret(lair_id, key, value)
        response.raise_for_status()

        self.assertNotIn('error', response.json())


if __name__ == '__main__':
    unittest.main()
