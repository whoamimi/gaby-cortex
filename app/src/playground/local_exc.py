"""
Minimal “LLM -> incremental Python exec -> stream outputs -> feed back” loop.

Key ideas:
- Keep a persistent Python state dict (`env`) across iterations.
- Force the LLM to output ONE JSON object per step: {"action":"run","code":"...","done":false}
- Execute code in-process, streaming stdout/stderr as it is written.
- On error, send the traceback back to the LLM and request a small patch.

Replace `call_llm_stream(...)` with your LLM provider (OpenAI, Gemini, local model, etc.).
"""

from __future__ import annotations

import io
import json
import queue
import threading
import traceback
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional, Any

class StreamingWriter(io.TextIOBase):
    def __init__(self, q: "queue.Queue[str]"):
        self.q = q

    def write(self, s: str) -> int:
        if s:
            self.q.put(s)
        return len(s)

    def flush(self) -> None:
        return


@dataclass(slots=True)
class ExecResult:
    ok: bool
    exception: Optional[str]
    traceback: Optional[str]

class PythonSession:
    """Persistent Python execution environment with streamed stdout/stderr."""
    def __init__(self) -> None:
        self.env: Dict[str, Any] = {}  # persistent globals

    def run_streaming(self, code: str) -> Iterator[str]:
        """
        Yields output chunks as the code runs.
        After completion, yields a final JSON line beginning with "__EXEC_RESULT__=".
        """
        out_q: "queue.Queue[str]" = queue.Queue()
        stdout = StreamingWriter(out_q)
        stderr = StreamingWriter(out_q)

        done_evt = threading.Event()
        result_holder: Dict[str, ExecResult] = {}

        def _runner() -> None:
            try:
                # Compile first: catches SyntaxError before running anything
                compiled = compile(code, "<llm_cell>", "exec")
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    exec(compiled, self.env, self.env)
                result_holder["result"] = ExecResult(ok=True, exception=None, traceback=None)
            except Exception as e:
                tb = traceback.format_exc()
                result_holder["result"] = ExecResult(ok=False, exception=repr(e), traceback=tb)
            finally:
                done_evt.set()

        t = threading.Thread(target=_runner, daemon=True)
        t.start()

        # Stream outputs while running
        while not done_evt.is_set() or not out_q.empty():
            try:
                chunk = out_q.get(timeout=0.05)
                yield chunk
            except queue.Empty:
                pass

        res = result_holder.get("result", ExecResult(ok=False, exception="Unknown", traceback="No result."))
        yield "__EXEC_RESULT__=" + json.dumps(res.__dict__, ensure_ascii=False)


# ---------------------------
# 2) LLM adapter (replace me)
# ---------------------------

SYSTEM_PROMPT = """You are driving a Python REPL.
You MUST reply with exactly one JSON object and nothing else.
Schema:
{
  "action": "run" | "stop",
  "code": "python code to execute (required if action=run)",
  "done": true | false,
  "notes": "optional short note"
}
Rules:
- No markdown. No backticks. No prose outside JSON.
- Keep code <= 40 lines per step.
- Code must be idempotent when possible.
"""

def call_llm_stream(messages: List[Dict[str, str]]) -> Iterator[str]:
    """
    Placeholder streaming generator.

    Replace with your provider. The function must yield text tokens/chunks.
    For quick testing, we hardcode a single step that prints and then stops.
    """
    # Example JSON (streamed in chunks to simulate real streaming)
    payload = {
        "action": "run",
        "code": "x = 1\nprint('x=', x)\n",
        "done": True,
        "notes": "demo"
    }
    s = json.dumps(payload, ensure_ascii=False)
    # simulate streaming chunks
    for i in range(0, len(s), 20):
        yield s[i : i + 20]


def collect_one_json_from_stream(stream: Iterator[str]) -> Dict[str, Any]:
    """
    Collects the full streamed response, then parses JSON.

    In production, use stronger framing (e.g., SSE events, length-prefix, or a strict JSON mode).
    """
    buf = []
    for chunk in stream:
        buf.append(chunk)
    raw = "".join(buf).strip()
    return json.loads(raw)

def controller_loop(user_goal: str, max_steps: int = 20) -> None:
    py = PythonSession()
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_goal},
    ]

    for step in range(1, max_steps + 1):
        llm_stream = call_llm_stream(messages)
        msg = collect_one_json_from_stream(llm_stream)

        action = msg.get("action")
        if action == "stop":
            print("\n[controller] LLM requested stop.")
            return

        if action != "run":
            raise ValueError(f"Unexpected action: {action!r}")

        code = msg.get("code", "")
        if not isinstance(code, str) or not code.strip():
            raise ValueError("Missing/empty 'code' for action=run.")

        print(f"\n[controller] STEP {step}: executing...\n")

        # Execute and stream output live
        exec_result: Optional[Dict[str, Any]] = None
        for out in py.run_streaming(code):
            if out.startswith("__EXEC_RESULT__="):
                exec_result = json.loads(out.split("=", 1)[1])
            else:
                print(out, end="")

        if exec_result is None:
            raise RuntimeError("No execution result received.")

        # Feed execution result back to LLM
        if exec_result["ok"]:
            messages.append({"role": "assistant", "content": json.dumps(msg)})
            messages.append({"role": "user", "content": f"Execution OK. Continue. (If finished, set done=true and action=stop.)"})
            if bool(msg.get("done")):
                print("\n[controller] done=true; stopping.")
                return
        else:
            tb = exec_result.get("traceback") or ""
            # Ask for a minimal patch
            messages.append({"role": "assistant", "content": json.dumps(msg)})
            messages.append({
                "role": "user",
                "content": (
                    "Execution failed with traceback below.\n"
                    "Return a JSON step that fixes the issue with minimal edits.\n\n"
                    + tb
                ),
            })

    print("\n[controller] max_steps reached; stopping.")


if __name__ == "__main__":
    controller_loop("Compute a small example and print intermediate results.")