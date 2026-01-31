"""
app/src/agent/rl.py

Agent Reinforcement Learning Module for Data Processing Pipelines.
TODO: Cleanup & Expand documentation.

References:
https://gibberblot.github.io/rl-notes/single-agent/multi-armed-bandits.html
https://arxiv.org/abs/1204.5721
https://gibberblot.github.io/rl-notes/single-agent/policy-based.html
https://hvrlxy.github.io/assets/pdfs/PageRank.pdf

"""

import random
import pandas as pd
from .base import Action, AgentDataset, AgentRLBuilder, StateMessage

# DB Model Session Fields
MEMORY_FIELD_NAME = [
    "stage",
    "response",
    "whisper_response",
    "inputs",
    "response_id",
    "model_version",
    "success",
    "statusCode",
    "errorMessage",
    "environment",
    "timestamp"
]
MEMORY_FIELD_MAP = {
    "stage": str,
    "response": str,
    "whisper_response": str,
    "inputs": dict,
    "response_id": str,
    "model_version": str,
    "success": bool,
    "statusCode": int,
    "errorMessage": str,
    "environment": str,
    "timestamp": str
}

# Streaming UI Elements
TREE_UI_ROOT = ("├──", "│", "└──", "──", "──>", "──o", "o──")
TREE_UI_DOT = ("•", "◦", "◉", "◎", "●")
TREE_UI_CHECKPOINT = ("✔", "✘", "➜", "➔")
TREE_UI_ARROWS = ("→", "←", "↑", "↓", "↳", "⇒", "⇐", "⇑", "⇓")
TREE_UI_STATUS = ("[+]", "[-]", "[~]", "[!]", "[?]")

class AgentCortex(AgentRLBuilder):
    def view_memory_tabular(self):
        """ Returns a tabular summary of the agent's memory and decisions. """
        if len(self.memory) == 0:
            return None
        df = pd.DataFrame(self.memory, columns=MEMORY_FIELD_NAME)

        return df.to_markdown(index=False)

    def view_policy_tabular(self):
        """ Returns a tabular summary of the agent's policy matrix. """
        if len(self.policyMatrix) == 0:
            return None
        df = pd.DataFrame.from_dict(self.policyMatrix, orient='index')
        return df.to_markdown(index=False)

    def view_stream(self):
        """ Returns a visual representation of the agent's decision-making process to display in terminal UI. """

        coll = []
        tabs = "\t"

        for state, action in self.policyMatrix.items():
            action_space_list = list(action.space.items())
            chosen_idx = list(action.space.keys()).index(action.action)
            prefix_content = tabs + TREE_UI_STATUS[0] + " [STATE: " + state + "]" + "\n"

            if not action_space_list:
                print("(empty)")
            elif len(action_space_list) == 1:
                k, v = action_space_list[0]
                print(tabs + f"{TREE_UI_ROOT[-1]}[{v}]{k}")
            else:
                k0, v0 = action_space_list[0]
                kN, vN = action_space_list[-1]

                a_first = tabs + f"{TREE_UI_ROOT[0]}[{v0}] {k0}\n"
                a_mid   = "\n".join([tabs + f"{TREE_UI_ROOT[0]}[{v}] {k}" if idx != chosen_idx else tabs + f"{TREE_UI_ROOT[0]}[{v}] {k} {TREE_UI_DOT[2]}" for idx, (k, v) in enumerate(action_space_list[1:-1], start=1)])
                a_last  = tabs + f"{TREE_UI_ROOT[2]}[{vN}] {kN}\n"

                if chosen_idx == 0 or chosen_idx == len(action_space_list) - 1:
                    if chosen_idx == 0:
                        a_first = tabs + f"{TREE_UI_ROOT[0]}[{v0}] {k0} {TREE_UI_DOT[2]}\n"
                    else:
                        a_last  = tabs + f"{TREE_UI_ROOT[2]}[{vN}] {kN} {TREE_UI_DOT[2]}\n"

                print(prefix_content + a_first + a_mid + "\n" + a_last)
                coll.append(prefix_content + a_first + a_mid + "\n" + a_last)

            tabs += "\t"
            return coll

    def select_action(self, current_stage: str, action_space: list, session: AgentDataset) -> Action:
        """ Returns the optimal action unique to the current session and current state.

        Seen state?
        1. Yes -> Return best action from policy matrix
        2. No  -> Randomly Selects action from action space.

        Args:
            action_space (list): List of possible actions to choose from.
            session (AgentDataset): Current dataset session containing state information.

        Returns:
            Action: Selected action with associated probability and action space.
        """
        fieldPattern = session.fieldPattern

        obs_state = [state for state in self.states if state.stage == current_stage]

        if self.actions.get(fieldPattern, None):
            v = []
            for act in self.actions[fieldPattern]:
                if not set(act.space.keys()) == set(action_space):
                    raise ValueError("Action space mismatch with recorded actions.")
                v.append(act.space)

            proba = np.vstack(v)
            proba /= proba.sum(axis=0)

            chosen = action_space[np.argmax(proba)]
            prob = np.max(proba)
        else:
            # If not seen similar state, randomly select action
            n = len(action_space)
            proba = [ 1 / n ] * n
            prob = proba[0]
            chosen = random.choices(action_space, weights=proba, k=1)[0] if n > 1 else action_space[0]

        return Action(action=chosen, proba=prob, space=dict(zip(action_space, proba)))

    def update(self, state: StateMessage, fieldPattern: str):
        """ Update the agent's memory based on the taken action and resulting state. """

        self.states.append(state)
        self.actions.setdefault(fieldPattern, []).append(state.action)

import numpy as np

DAMPING_FACTOR = 0.85
EPS = 1.0e-6

class PageRanker:
    """
    PageRank Algorithm Implementation for Web Page Ranking.
    https://hvrlxy.github.io/assets/pdfs/PageRank.pdf

    """
    def __init__(self, graph: dict, **kwargs):
        """ Initialize PageRanker with graph structure."""
        self.d = kwargs.get("damping_factor", DAMPING_FACTOR)
        self.epsilon = kwargs.get("epsilon", EPS)
        self.reset(graph)

    @property
    def teleport(self):
        return (1.0 - self.d) / self.N

    def reset(self, graph: dict):
        """ Setup internal graph structure from adjacency list. """

        if not hasattr(self, "nodes"):
            self.nodes = set()
        if not hasattr(self, "graph"):
            self.graph = {}

        for node, outlinks in graph.items():
            for outlink in outlinks:
                if outlink not in self.graph:
                    self.graph.setdefault(node, []).append(outlink)
                if node not in self.nodes:
                    self.nodes.add(node)

        #self.nodes = sorted(tuple(set(graph.keys()) | set([t for targets in graph.values() for t in targets])))
        self.N = len(self.nodes)
        self.tag2idx = {tag: idx for idx, tag in enumerate(self.nodes)}
        self.idx2tag = {idx: tag for idx, tag in enumerate(self.nodes)}

        if not hasattr(self, 'adj'):
            self.adj = np.zeros((self.N, self.N))

    def update(self, graph: dict):
        """ Update adjacency matrix based on new graph structure.

        Build the Google matrix M of size N x N:

            M[i, j] = probability of transitioning from page j to page i

        (column-stochastic form).

        """
        self.reset(graph)

        missed = {}
        for key, outlinks in graph.items():
            assert isinstance(outlinks, list) and isinstance(key, str), "Outlinks must be a list."
            i = self.tag2idx.get(key, None)

            if i is None:
                print(f"The term: {key} has not been seen by model. Skipping update.")
                missed[key] = outlinks
            else:
                for outlink in outlinks:
                    j = self.tag2idx[outlink]
                    curr = self.adj[i, j]
                    self.adj[i, j] = self.teleport + self.d * curr
                    print(f"from {curr} to {self.adj[i, j]}")

                self.adj[i, :] /= self.adj[i, :].sum()

        return missed

    def predict(self, current: str):
        """ Given a current node, return outlink probabilities. """

        if current not in self.tag2idx:
            print("Queried key not in graph:", current)
            return None

        i = self.tag2idx[current]
        outlinks = self.adj[i, :]
        prob = {self.idx2tag[j]: outlinks[j] for j in range(len(outlinks))}
        return sorted(prob.items(), key=lambda x: x[1], reverse=True)

