""" app/src/playground/local_tools.py

Agent tools to run Python code in a separate background process in the local environment.
"""

from __future__ import annotations

import os
import re
import sys
import time
import json
import uuid
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union, Sequence

from ..agent.registry import Toolbox

agent_kernel_tools = Toolbox("agent_kernel_tools")

_CODE_FENCE_RE = re.compile(r"```(?:python)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)

def extract_python_code(text: str) -> str:
    """
    Extract the FIRST ```python ... ``` (or ``` ... ```) fenced block.
    Falls back to raw text if no fences are found.
    """
    if not isinstance(text, str):
        raise TypeError(f"Expected str for code extraction, got {type(text)!r}")

    m = _CODE_FENCE_RE.search(text)
    return (m.group(1) if m else text).strip()

@dataclass(slots=True)
class ExecOutcome:
    ok: bool
    returncode: int
    stdout: str
    stderr: str
    duration_s: float
    script_path: str
    workdir: str

@agent_kernel_tools
def execute_python_safely(
    code: str,
    *,
    tmp_root: Path,
    timeout_s: int = 30,
    python_exe: str = sys.executable,
) -> ExecOutcome:
    """
    Executes code in a temp directory as a real Python process, capturing stdout/stderr.
    - Writes code to a temp .py file
    - Runs it with a hard timeout
    - Captures stdout/stderr
    """
    tmp_root.mkdir(parents=True, exist_ok=True)

    run_id = uuid.uuid4().hex[:12]
    workdir = tmp_root / f"exec_{run_id}"
    workdir.mkdir(parents=True, exist_ok=True)

    script_path = workdir / "script.py"
    script_path.write_text(code, encoding="utf-8")

    start = time.monotonic()
    try:
        proc = subprocess.run(
            [python_exe, str(script_path)],
            cwd=str(workdir),
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        dur = time.monotonic() - start
        return ExecOutcome(
            ok=(proc.returncode == 0),
            returncode=proc.returncode,
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
            duration_s=dur,
            script_path=str(script_path),
            workdir=str(workdir),
        )
    except subprocess.TimeoutExpired as e:
        dur = time.monotonic() - start
        return ExecOutcome(
            ok=False,
            returncode=124,
            stdout=(e.stdout or ""), # type: ignore
            stderr=(e.stderr or "") + f"\n[timeout] exceeded {timeout_s}s", # type: ignore
            duration_s=dur,
            script_path=str(script_path),
            workdir=str(workdir),
        )

@agent_kernel_tools
def run_code_execution(llm, response: Any, max_retries: int = 3, max_debug_duration_s: int = 90, per_run_timeout_s: int = 30, tmp_dir: Path = Path("./TMP")):
    """
    Retrieves the code block from LLM and executes it.
    On failure, retries with an automated debug loop until:
        - success, OR
        - max_retries reached, OR
        - max_debug_duration_s exceeded

    Returns a structured result (you can adapt to your framework).
    """
    script_code = extract_python_code(response)

    # 1) Retry loop with wall-clock budget
    attempt = 0
    started = time.monotonic()
    last_outcome: Optional[ExecOutcome] = None

    while True:
        elapsed = time.monotonic() - started
        if elapsed > max_debug_duration_s:
            break
        if attempt > max_retries:
            break

        attempt += 1

        outcome = execute_python_safely(
            script_code,
            tmp_root=tmp_dir,
            timeout_s=per_run_timeout_s,
        )
        last_outcome = outcome

        # 2) Persist logs for post-mortem (always)
        #    Each attempt has its own workdir; write a concise metadata file too.
        meta_path = Path(outcome.workdir) / "meta.json"
        meta_path.write_text(
            json.dumps(
                {
                    "attempt": attempt,
                    "ok": outcome.ok,
                    "returncode": outcome.returncode,
                    "duration_s": outcome.duration_s,
                    "script_path": outcome.script_path,
                    "workdir": outcome.workdir,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        (Path(outcome.workdir) / "stdout.txt").write_text(outcome.stdout, encoding="utf-8")
        (Path(outcome.workdir) / "stderr.txt").write_text(outcome.stderr, encoding="utf-8")

        if outcome.ok:
            # Success: return structured results
            return {
                "status": "ok",
                "attempts": attempt,
                "debug_duration_s": time.monotonic() - started,
                "workdir": outcome.workdir,
                "stdout": outcome.stdout,
                "stderr": outcome.stderr,
                "script_path": outcome.script_path,
            }

        # 3) Failure: construct a minimal “debug context” and request a patched script
        #    This assumes you have some method to call your LLM again.
        #    If your framework already handles multi-turn repair, replace this block accordingly.
        debug_context = {
            "attempt": attempt,
            "max_retries": max_retries,
            "elapsed_s": round(time.monotonic() - started, 3),
            "returncode": outcome.returncode,
            "stderr_tail": outcome.stderr[-4000:],  # cap size
            "stdout_tail": outcome.stdout[-4000:],
            "hint": "Return ONLY a corrected ```python``` code block. Keep changes minimal.",
        }

        # If you have a built-in agent call method, use it here:
        # response = self.call_llm({"code": script_code, "debug": debug_context, ...})
        # raw = get_response(response, "executor")
        # script_code = extract_python_code(raw)

        # Placeholder: stop retrying if you cannot actually request patches here.
        # Remove this early exit once you wire in your LLM repair call.
        break

    # 4) Exhausted retries or budget: return failure payload
    return {
        "status": "failed",
        "attempts": attempt,
        "debug_duration_s": time.monotonic() - started,
        "last_workdir": (last_outcome.workdir if last_outcome else None),
        "last_stdout": (last_outcome.stdout if last_outcome else ""),
        "last_stderr": (last_outcome.stderr if last_outcome else ""),
        "message": "Execution failed: exceeded retry limit or debug duration.",
    }