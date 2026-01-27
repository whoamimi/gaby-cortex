""" app/src/agent/registry.py
"""

import inspect
import docstring_parser
from functools import wraps
from google.genai import types
from typing import get_type_hints, Any

from ...utils.woodlogs import setup_logger

logger = setup_logger(__file__)

class Toolbox:
    """ Class decorator that registers all tool/action functions defined in this module. """

    _shed: dict[str, dict[str, Any]] = {}

    def __init__(self, workflow: str):
        """ Args workflow is the name of the group of tools being registered. """

        if workflow not in Toolbox._shed:
            logger.info(f'First time registering {workflow}')
            Toolbox._shed[workflow] = {}

        self.current_workflow = workflow

    @classmethod
    def list_workflows(cls):
        return list(Toolbox._shed)

    @classmethod
    def get_action(cls, workflow_name: str, function_name: str):
        """ Returns the requested function. This is for the agent to use to call action by itself. """
        if tool := Toolbox._shed.get(workflow_name, {}).get(function_name, None):
            return types.Tool(function_declarations=[tool])

        else:
            return None

    def __call__(self, func):
        """Called when used as a decorator."""

        tool_name = func.__name__

        sig = inspect.signature(func)
        type_hints = get_type_hints(func)
        doc = func.__doc__ or "Unknown"
        parsed_doc = docstring_parser.parse(doc)

        # Map docstring arg descriptions
        doc_args = {p.arg_name: p.description for p in parsed_doc.params}

        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            annotation = type_hints.get(param_name, str)
            if annotation in (int, "int"):
                arg_type = "integer"
            elif annotation in (float, "float"):
                arg_type = "number"
            elif annotation in (bool, "bool"):
                arg_type = "boolean"
            else:
                arg_type = "string"

            if param.default == inspect._empty:
                required.append(param_name)

            desc = doc_args.get(param_name, f"Argument `{param_name}` of type {arg_type}")
            properties[param_name] = {"type": arg_type, "description": desc}

        # Register function metadata and callable
        Toolbox._shed[self.current_workflow][tool_name] = {
            "name": tool_name,
            "description": parsed_doc.short_description or doc.strip(),
            "parameters": dict(
                type="object",
                properties=properties,
                required=required,
            ),
        }

        logger.info(f"Registered tool: {tool_name} under workflow: {self.current_workflow}")
        Toolbox._shed[self.current_workflow][tool_name] = func

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

