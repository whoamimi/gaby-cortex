""" app/src/tools/execution.py

Agent tools to run Python code in a separate background process.
"""
from __future__ import annotations

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional, Union, Sequence

from ..agent.registry import Toolbox 

agent_kernel_tools = Toolbox("agent_kernel_tools")

@agent_kernel_tools
def run_python_in_background(
    *,
    script_path: Optional[Union[str, Path]] = None,
    code: Optional[str] = None,
    args: Optional[Sequence[str]] = None,
    cwd: Optional[Union[str, Path]] = None,
    env: Optional[dict] = None,
    stdout_path: Union[str, Path] = "agent_stdout.log",
    stderr_path: Union[str, Path] = "agent_stderr.log",
) -> subprocess.Popen:
    """
    Run Python code in a separate background process.

    Provide exactly one of:
      - script_path: path to a .py file
      - code: a Python source string

    Returns a subprocess.Popen handle (pid, poll(), terminate(), kill(), wait()).
    """

    if (script_path is None) == (code is None):
        raise ValueError("Provide exactly one of script_path or code.")

    args = list(args or [])
    cwd = str(cwd) if cwd is not None else None

    cmd = [sys.executable]
    if script_path is not None:
        cmd += [str(script_path), *args]
    else:
        cmd += ["-c", code, *args]

    # Ensure parent directories exist
    stdout_path = Path(stdout_path)
    stderr_path = Path(stderr_path)
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)

    # Start process without blocking
    stdout_f = open(stdout_path, "ab", buffering=0)
    stderr_f = open(stderr_path, "ab", buffering=0)

    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        env=(os.environ | env) if env else None,
        stdout=stdout_f,
        stderr=stderr_f,
        stdin=subprocess.DEVNULL,
        start_new_session=True,  # detaches from parent terminal/session
        text=False,
    )

    return proc