"""
app/src/agent/methods.py

Agent Builder Helper Methods and Utilities.
"""

from typing import Any
from .types import DATA_TRANS_ACTIONS

def getAction(stage: str):
    """ Returns the vectors of action labels for a given transformation stage. """

    try:
        if stageAction := DATA_TRANS_ACTIONS.get(stage, None):
            yield from list(stageAction.items())
        else:
            raise KeyError(f"Unknown transformation stage '{stage}'")
    except KeyError as e:
        raise e
    except StopIteration:
        return None

def getActionSummary(stage: str):
    """ Returns textual summary of action labels for a given transformation stage. """

    return "".join(
        f"{label}: {description}\n" for label, description in getAction(stage)
    )

def getActionLabels(stage: str):
    """ Returns list of action labels for a given transformation stage. """

    return [label for label, _ in getAction(stage)]


