# tests/agent/test_playground.py

import unittest
from app.src.playground.local import JupyterConnector

DEMO_CREATE_NEW_SESSION_RESPONSE = {
    'id': 'eb024af4-6bd7-4c9e-bbcd-5fab540a1fba',
    'path': 'test-session-id.ipynb',
    'name': 'test-session-id',
    'type': 'notebook',
    'kernel': {
        'id': 'feda4ad6-53e8-4e65-b970-9b5f86c21935',
        'name': 'python3', 'last_activity': '2026-01-20T11:19:31.306623Z', 'execution_state': 'starting', 'connections': 0},
    'notebook': {'path': 'test-session-id.ipynb', 'name': 'test-session-id'}
}
DEMO_HEALTH_CHECK_RESPONSE = {
    'connections': 0,
    'kernels': 0,
    'last_activity': '2026-01-20T10:42:45.319492Z',
    'started': '2026-01-20T09:45:06.702502Z'
}

DEMO_WS_RESPONSE_EXECUTION_REPLY = {
    'header': {
        'msg_id': '9da31539-4c8526a7e498426c14657795_86_440',
        'msg_type': 'execute_reply',
        'username': 'username',
        'session': '9da31539-4c8526a7e498426c14657795',
        'date': '2026-01-20T12:35:45.741969Z',
        'version': '5.3'
    },
    'msg_id': '9da31539-4c8526a7e498426c14657795_86_440',
    'msg_type': 'execute_reply',
    'parent_header': {'msg_id': 'f37440ead2054f2d9a636f5760984d42', 'username': 'agent', 'session': 'eb024af4-6bd7-4c9e-bbcd-5fab540a1fba', 'msg_type': 'execute_request', 'date': '2026-01-20T12:35:42.398254+01:00', 'version': '5.1'},
    'metadata': {'started': '2026-01-20T12:35:45.734952Z', 'dependencies_met': True, 'engine': '62981e5b-ecc5-4e65-a323-777d999b720f', 'status': 'ok'},
    'content': {'status': 'ok', 'execution_count': 37, 'user_expressions': {}, 'payload': []},
    'buffers': [],
    'channel': 'shell'
}
# THIS IS CUSTOM TO MY MODULE NOT THE RAW OUTPUT
DEMO_WS_EXECUTION_RESULT = {
    'session_id': 'eb024af4-6bd7-4c9e-bbcd-5fab540a1fba',
    'kernel_id': 'feda4ad6-53e8-4e65-b970-9b5f86c21935',
    'msg_id': 'f37440ead2054f2d9a636f5760984d42',
    'status': 'ok',
    'outputs': [{'type': 'stream', 'name': 'stdout', 'text': 'Running Virtual Calculator 2 + 2 = 4\n'}],
    'execute_reply': {'status': 'ok', 'execution_count': 37, 'user_expressions': {}, 'payload': []}
}

class TestJupyterConnector(unittest.TestCase):
    def setUp(self):
        self.connector = JupyterConnector()

    def test_send_request_healthy_status(self):
        output = self.connector._send_request("status")

        if output is not None and isinstance(output, dict):
            self.assertSetEqual(set(output.keys()), set(DEMO_HEALTH_CHECK_RESPONSE.keys()), f"Response keys do not match expected keys. {output.keys()} vs {DEMO_HEALTH_CHECK_RESPONSE.keys()}")
        else:
            self.fail(f"Health check failed or response is None. Response: {output}")
