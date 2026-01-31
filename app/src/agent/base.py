""" src/agent/registry.py

Class for building Agents in this module.


"""

from __future__ import annotations

import pickle
import uuid
import datetime
from mock import DEFAULT
import pandas as pd
from enum import Enum
from pathlib import Path
from abc import ABC, abstractmethod
from collections import OrderedDict
from typing import Any, Literal, Tuple, List
from dataclasses import dataclass, field

from ...utils.woodlogs import setup_logger
from .hostess import GenAIMessage, GoogleGenAIProvider, DEFAULT_KWARGS
from .types import AgentTabularFields, DataTypeCategories

logger = setup_logger(__name__)

@dataclass(slots=True)
class Action:
    """ Data Model for how Action MetaData is stored for agent. """
    action: str
    proba: float
    space: dict

    @property
    def space_vector(self):
        """ Returns the action space vector as a tuple. """
        return list(self.space.keys()) if len(self.space) > 0 else []

    @property
    def n(self):
        """ Returns the number of possible actions in the action space. """
        return len(self.space_vector)

@dataclass(slots=True)
class StateMessage:
    """ Data Model for how State Messages are stored for agent. """
    stage: str
    response: str
    llm_response: Any | None = None
    whisper_response: Any | None = None
    # inputs
    inputs: GenAIMessage | None = None
    # state env config / llm metadata
    response_id: str | None = None
    model_version: str | None = None
    decoder_kwargs: dict | None = None
    # agent RL metadata
    action: Action | None = None
    # system traces
    success: bool = False
    statusCode: int | None = 200
    errorMessage: str | None = None
    # session traces
    sessionId: str | uuid.UUID = field(default=uuid.uuid4().hex)
    eventId: str | uuid.UUID = field(default=uuid.uuid4().hex)
    environment: Literal["local", "kaggle-kernel", "hf-kernel", "gcloud"] = "local"
    timestamp: datetime.datetime = field(default=datetime.datetime.now(datetime.UTC))

    def __post_init__(self):
        logger.info(f"StateMessage initialized with success: {self.success} at {self.timestamp}")

        if self.success is False and not self.errorMessage:
            self.errorMessage = "StateMessage failed without specific error message."
            logger.warning("StateMessage failed without specific error message.")
        if self.success is False and self.statusCode == 200:
            logger.warning("StateMessage failed but statusCode was 200. Setting to 500. Pls reset to appropriate code.")
            self.statusCode = 500

        if isinstance(self.sessionId, uuid.UUID):
            self.sessionId = str(self.sessionId)
        if isinstance(self.eventId, uuid.UUID):
            self.eventId = str(self.eventId)

class AgentBasement(ABC):
    """ Base AgentBuilder class for defining Agents. """

    @abstractmethod
    def postprocess(self, *args, **kwargs) -> StateMessage:
        """ Postprocess the LLM response and return them as state responses: CognitiveState and StateMessage. """
        pass

    @abstractmethod
    def preprocess(self, profiler: Any, **kwargs) -> dict:
        """ Preprocess the data profiling and prepare the raw message dict to be formatted by input_format before passing to LLM.
        """
        pass

    def __call__(self, llm: GoogleGenAIProvider, session: AgentDataset, decode_kwargs: dict = {}, **kwargs):
        """ Generic Caller for all agents.
        [self.preprocess + self.augement_dataset] -> self._preprocessor --> llm --> self.postprocess
        """

        decode_kwarg = {k: kwargs.get(k, v) for k, v in llm.default.items()} if decode_kwargs else llm.default.copy()

        raw_message: dict = self.preprocess(session, **kwargs)
        inputs: GenAIMessage = self._preprocessor(raw_message, **decode_kwarg)
        response = llm(inputs)
        output: StateMessage = self.postprocess(response)

        output.sessionId = session.id
        output.inputs = inputs
        output.decoder_kwargs = inputs.decoder_kwargs
        output.model_version = llm.model_id
        output.response_id = response.response_id if hasattr(response, "response_id") else None
        output.llm_response = response

        return output, session

    def __init_subclass__(cls, prompt: Enum | str, input_format: Enum | str, **kwargs) -> None:
        """ Generic initializer for all Agents built in this module. """
        cls.prompt = prompt.value if isinstance(prompt, Enum) else prompt
        cls.input_format = input_format.value if isinstance(input_format, Enum) else input_format
        logger.debug(f"Initialized SkeletonAgent subclass: {cls.__qualname__} with prompt role: {prompt.name if isinstance(prompt, Enum) else prompt}")
        return super().__init_subclass__(**kwargs)

    def _preprocessor(self, formatted_response: dict, **kwargs):
        """ Generic Preprocessor to format the raw message dict into GenAIMessage format before passing to LLM.  """

        if not isinstance(formatted_response, dict): raise TypeError(f"{self.__class__.__qualname__} defined `preprocess` method must return a dict.")

        return GenAIMessage(
            system_instruction=self.prompt,
            content=self.input_format.format(**formatted_response),
            decoder_kwargs=kwargs
        )

    def extract_text_from_response(self, response: Any):
        """ Generic postprocess method to extract text from LLM response text only. """
        return GoogleGenAIProvider._extract_text_from_response(response)

class AgentPipeline(OrderedDict):
    """ Base Agent Pipeline Controller class to orchestrate an sequential workflows. """
    @abstractmethod
    def execute_pipeline(self, llm: GoogleGenAIProvider, session: AgentDataset, **kwargs):
        """ Main method to execute the agent pipeline through all stages. """
        pass

    def __init__(self):
        super().__init__()

        for k, v in self.__class__.__dict__.items():
            if isinstance(v, type) and (issubclass(v, AgentBasement) or issubclass(v, AgentPipeline)):
                self[k.lower().strip()] = v()
                logger.debug(f"Added stage '{k}' to AgentPipeline '{self.__class__.__qualname__}'")

    def __init_subclass__(cls, *args, **kwargs) -> None:
        """ Generic initializer for all AgentPipeline built in this module. """
        logger.debug(f"Initialized AgentPipeline subclass: {cls.__qualname__}")
        cls.label = cls.__class__.__qualname__
        return super().__init_subclass__(*args, **kwargs)

    def __repr__(self) -> str:
        stage_names = ', '.join(self.keys())
        return f"{self.__class__.__qualname__} with stages: [{stage_names}]"

@dataclass(slots=True)
class AgentDataset:
    """ Base Session Dataset where child subclass are used to pass data to agents. """

    # Session Inputs & Metadata
    ds: pd.DataFrame
    id: str | uuid.UUID = field(default=uuid.uuid4().hex)
    timestamp: datetime.datetime = field(default=datetime.datetime.now(datetime.UTC))

    # Unique Identifiers for Dataset State
    fieldPattern: str = field(init=False)
    fieldPostPattern: str | None = field(init=False, default=None)
    profiler: str | None = field(init=False, default=None)
    postOutput: pd.DataFrame | None = field(init=False, default=None)

    # Tabular Reports Config/Utils
    tabularConfig = AgentTabularFields
    tabularUtils = DataTypeCategories

    def __post_init__(self):
        logger.info(f"Dataset initialized for AgentDataset with ID: {self.id} at {self.timestamp}. Size: {self.ds.shape if isinstance(self.ds, pd.DataFrame) else len(self.ds)}")
        self.profiler = self.get_data_profiler_string()
        self.fieldPattern = self.assign_code(self.ds)
        logger.info(f"Assigned fieldPattern: {self.fieldPattern} for dataset ID: {self.id}")

    def _generate_dtype_code(self, dtype_dict: dict | pd.Series, codeConfig: dict) -> str:
        """ Helper method to generate dtype code from dtype dict and config map. """

        code_ = {}
        for _, dtype_label in dtype_dict.items():
            dtype = str(dtype_label)

            if dtype not in code_:
                code_[dtype] = 0

            code_[dtype] += 1

        for k in codeConfig:
            code_.setdefault(k, 0)

        return "".join([f"{codeConfig.get(d, "UNO")}{count}" for d, count in code_.items() if codeConfig.get(d, None)])

    def assign_code(self, df: pd.DataFrame):
        """ Returns unique code representing the data types in the dataframe. """
        if "data_type_category" in df.columns and "data_type_subcategory" in df.columns:
            parentConfig = self.tabularUtils.codeDtype.value.categoryCode.value
            childConfig = self.tabularUtils.codeDtype.value.subCode.value
            parentDtype = df.set_index("data_field_name")["data_type_category"].to_dict()
            childDtype = df.set_index("data_field_name")["data_type_subcategory"].to_dict()
            return self._generate_dtype_code(parentDtype, parentConfig) + self._generate_dtype_code(childDtype, childConfig)

        else:
            return self._generate_dtype_code(df.dtypes, self.tabularUtils.codeDtype.value.pandasDtype.value)

    @staticmethod
    def get_data_profiler(ss: pd.DataFrame):
        """
        Generate data profile summary for the given dataset.

        :param ss: Current Session Dataset object containing the dataset to be profiled.
        :type ss: AgentDataset
        """

        data_types = ss.dtypes.to_dict()
        data_nulls = ss.isnull().sum().to_dict()
        data_stats = ss.describe(include="all").T.reset_index().rename(columns={"index": "data_field_name", "unique": "unique_counts"})
        data_stats["data_type"] = data_stats["data_field_name"].map(data_types)
        data_stats["null_counts"] = data_stats["data_field_name"].map(data_nulls)

        return data_stats[AgentTabularFields.SUMMARY.value]

    def get_data_profiler_string(self):
        """ Returns the data profiler as a string. """
        df: pd.DataFrame = self.get_data_profiler(self.ds)
        return df.to_string(header=True, index=False)

# Agent RL Builders
LAST_K = 3
DISCOUNT_FACTOR = 0.5
CHECKPOINT_DIR_PATH = Path("outputs/checkpoints/")
CHECKPOINT_FILE_PATH = CHECKPOINT_DIR_PATH / "rl_matrix.pkl"

class AgentRLBuilder(ABC):
    """ Agent RL Base Class for building Reinforcement Learning based agents in this module. """
    def __init__(self, reference_matrix_path: Path | None = None, **kwargs):
        self.states = []
        self.actions = OrderedDict()
        self.last_k = kwargs.get("last_k", LAST_K)
        self.discount_factor = kwargs.get("discount_factor", DISCOUNT_FACTOR)
        self.checkpoint_path = kwargs.get("checkpoint_path", CHECKPOINT_FILE_PATH)

    @abstractmethod
    def select_action(self, **kwargs) -> Action:
        """ Returns the optimal action relative to the implemented RL method."""
        pass

    @abstractmethod
    def update(self, **kwargs):
        """ Update the agent's internal state or model. """
        pass

    @property
    def temporal_lobe(self):
        """ Returns last recent N memories for short-term context. """
        return self.states[-self.last_k:] if len(self.states) > self.last_k else self.states

    @property
    def N(self):
        """ Returns the total number of unique states observed. """
        return len(self.states)

    @classmethod
    def load_from_checkpoint(cls, checkpoint_path: Path):
        """ Load an agent instance from a saved checkpoint. """

        if checkpoint_path.exists():
            with checkpoint_path.open("rb") as f:
                obj = pickle.load(f)
                return cls(**obj)
        else:
            raise FileNotFoundError(f"Checkpoint file not found at {checkpoint_path}")

    @classmethod
    def save_to_checkpoint(cls, checkpoint_path: Path, obj):
        """ Save the agent instance to a checkpoint. """

        with checkpoint_path.open("wb") as f:
            pickle.dump(obj, f)

