""" src/playground/jupyter_server.py

Jupyter Kernel Server REST API Connector hosted with local or private spaces.
https://jupyter-server.readthedocs.io/en/latest/developers/rest-api.html
"""

import sys
import json
import uuid
import requests
import datetime
from typing import Literal
from websocket import create_connection  # pip install websocket-client

from ... import workspace
from ...utils.woodlogs import setup_logger

logger = setup_logger(__name__)

DEFAULT_KWARGS = {
    "packages": ["numpy", "pandas", "matplotlib", "seaborn", "scikit-learn", "requests"]
}

class JupyterConnector:
    """
    Controller for Jupyter Kernel Server REST API. Hosted on Hugging Face Spaces or self-hosted.
    """

    def __init__(self,
            hf_token: str = workspace.secrets._hf_token,
            kernel_server: str = workspace.secrets.jupyter_kernel_server_url,
            timeout: int = workspace.secrets.jupyter_kernel_server_timeout,
            jupyter_api_key: str = workspace.secrets._jupyter_kernel_server_key,
            jupyter_socket_server: str = workspace.secrets.jupyter_kernel_server_socket,
            **kwargs
        ):

        self._timeout = timeout
        self.__hf_token = hf_token
        self.__jupyter_key = jupyter_api_key
        self.__kernel_server = kernel_server
        self.__socket_kernel_server = jupyter_socket_server
        self.__params = {"token": self.__jupyter_key}
        self.__headers = {
            "Authorization": f"Bearer {self.__hf_token}",
            "Content-Type": "application/json",
        }
        self.defaults = {k: kwargs.get(k, v) for k, v in DEFAULT_KWARGS.items()}
        self.health_check()

        # logger.info(self._send_request("me"))

    def _send_request(self, endpoint_suffix: str, method: Literal["GET", "POST"] = "GET", data: dict | None = None, params: dict = {}):
        try:
            if method == "POST" and data is None:
                raise ValueError("POST requests require a data payload.")

            endpoint_suffix = endpoint_suffix.lstrip("/") if endpoint_suffix and endpoint_suffix.startswith("/") else endpoint_suffix
            params = self.__params.copy()
            if params:
                params.update(params)

            url = f"{self.__kernel_server}/{endpoint_suffix}"
            response = requests.get(url, headers=self.__headers, params=params, timeout=self._timeout) if method == "GET" else requests.post(url, headers=self.__headers, params=params, json=data, timeout=self._timeout)

            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            logger.error(f"Request to {endpoint_suffix} failed: {e}")
            return None

    def health_check(self):
        """ Check Jupyter Kernel Server Status """
        output = self._send_request(endpoint_suffix="status")
        logger.info(f"Running Server Status for JupyterConnector: {output}")

    def list_kernels(self):
        output = self._send_request(endpoint_suffix="kernels")
        logger.info(f"Listing available kernels from Jupyter Kernel Server: {output}")

    def list_sessions(self):
        output = self._send_request(endpoint_suffix="sessions")
        logger.info(f"Listing active sessions from Jupyter Kernel Server: {output}")

    def list_terminals(self):
        output = self._send_request(endpoint_suffix="terminals")
        logger.info(f"Listing active terminals from Jupyter Kernel Server: {output}")

    ### SESSION CONTROLLERS
    def create_new_session(self, session_id: str, session_name: str | None = None):
        """ Creates a new session yielding notebook with Kernel attached. """

        payload = {
            "name": session_name if session_name else session_id,
            "path": f"{session_id}.ipynb",
            "type": "notebook",
        }

        ss = self._send_request(endpoint_suffix="sessions", method="POST", data=payload)

        if not isinstance(ss, dict):
            raise ValueError(f"Failed to create new session for ID: {session_id}")

        self.install_packages(session_id=session_id, kernel_id=ss.get("kernel", {}).get("id", None), packages=self.defaults["packages"])

        return ss

    ### EXECUTE CODE BLOCKS IN KERNEL
    def execute_code_block(self,
        session_id: str,
        kernel_id: str,
        code_block: str,
        msg_id: str = uuid.uuid4().hex,
        timestamp: str = datetime.datetime.now(datetime.UTC).isoformat()
    ):
        """
        Execute a code block in the specified Jupyter kernel using WebSocket.

        Args:
            session_id: The session identifier
            kernel_id: The kernel identifier
            code_block: Python code to execute

        Returns:
            dict: Execution results including outputs and status
        """

        ws_url = f"{self.__socket_kernel_server}/{kernel_id}/channels?token={self.__jupyter_key}"

        ws_request = {
            "header": {
                "msg_id": msg_id,
                "username": "agent",
                "session": session_id,
                "msg_type": "execute_request",
                "date": timestamp,
                "version": "5.1"
            },
            "parent_header": {},
            "metadata": {},
            "content": {
                "code": code_block,
                "silent": False,
                "store_history": True,
                "user_expressions": {},
                "allow_stdin": False,
                "stop_on_error": True
            },
            "channel": "shell"
        }

        stream_logs = {
            "session_id": session_id,
            "kernel_id": kernel_id,
            "msg_id": msg_id,
            "outputs": [],
            "status": None,
            "error": None,
            "execute_reply": None
        }

        ws = create_connection(
            ws_url,
            header=[f"Authorization: Bearer {self.__hf_token}"],
            timeout=self._timeout
        )

        try:
            ws.send(json.dumps(ws_request))
            logger.info(f"Sent execute request: {msg_id}")

            while True:
                msg = json.loads(ws.recv())
                # logger.info(f"[RAW] Received message: {msg}")

                msg_type = msg.get("msg_type", "")
                content = msg.get("content", {})

                if msg.get("parent_header", {}).get("msg_id") != msg_id:
                    continue

                if msg_type in ["stream", "execute_result", "display_data"]:
                    stream_logs["outputs"].append({
                        "type": msg_type,
                        "content": content,
                    })

                elif msg_type == "error":
                    raise RuntimeError(f"Error during code execution in Jupyter Notebook server: {content}")

                elif msg_type == "execute_reply":
                    stream_logs["status"] = content["status"]
                    stream_logs["execute_reply"] = content

                elif msg_type == "status" and content.get("execution_state") == "idle":
                    logger.info(f"Execution completed for msg_id: {msg_id}.")
                    break

        except Exception as e:
            logger.error(f"Failed to execute code block: {e}")
            stream_logs["error"] = str(e)
            stream_logs["status"] = "system_error"
        finally:
            ws.close()
            return stream_logs

    def install_packages(self, session_id: str, kernel_id: str, packages: list[str] | str):
        """
        Install Python packages in the kernel using pip.

        Args:
            session_id: The session identifier
            kernel_id: The kernel identifier
            packages: Package name(s) to install (string or list)

        Returns:
            dict: Installation results
        """
        if isinstance(packages, str):
            packages = [packages]

        package_list = " ".join(packages)
        install_code = f"import sys\n!{sys.executable} -m pip install {package_list}"

        logger.info(f"Installing packages: {package_list}")
        return self.execute_code_block(session_id, kernel_id, install_code)

    def execute_many(self, session_id: str, kernel_id: str, code_blocks: list[str]):
        """ Execute multiple code blocks sequentially in the specified kernel/notebook. """

        try:
            results = []
            for block in code_blocks:
                res = self.execute_code_block(session_id, kernel_id, block)
                results.append(res)

            return results
        except Exception as e:
            logger.error(f"Failed to execute multiple code blocks: {e}")
            return None

if __name__ == "__main__":
    TEST_KERNEL_NAME = "python3"
    TEST_KERNEL_ID = "feda4ad6-53e8-4e65-b970-9b5f86c21935"
    TEST_SESSION_NAME = "test-session-id"
    TEST_SESSION_ID = "eb024af4-6bd7-4c9e-bbcd-5fab540a1fba"
    TEST_CODE_BLOCK = "print('hello world from test code block')"
    pl = JupyterConnector()
    result = pl.execute_code_block(
        session_id=TEST_SESSION_ID,
        kernel_id=TEST_KERNEL_ID,
        code_block="print('Running Virtual Calculator 2 + 2 =', 2*2*2*2*2);"
    )
    logger.info(f"Execution result: {result}")