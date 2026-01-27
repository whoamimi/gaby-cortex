""" app/src/agent/chain.py

Agent Workflow Chains and Pipelines
"""

from __future__ import annotations

import re, json
from unittest import result
import pandas as pd
from typing import Any
from collections import OrderedDict

from .rl import AgentCortex
from .hostess import GoogleGenAIProvider
from .types import DataAgentInputsTemplate, DataAgentRoleConfig, SkeletonAgentInputs, SkeletonAgentRole
from .base import AgentDataset, StateMessage, AgentBasement, AgentPipeline

from ...utils.woodlogs import setup_logger

logger = setup_logger(__name__)

def get_response(obj, response: Any, stage_name: str = "planner") -> StateMessage:
    """ Generic response formatter for Skeleton Agent stages.  """

    exc: str | None = None
    txt: str = ""

    try:
        txt: str = obj.extract_text_from_response(response)
        model_version: str = response.model_version
        response_id: str = response.response_id

    except Exception as e:
        exc = str(e)
    finally:
        if exc:
            logger.error(f"Error in {stage_name.capitalize()} postprocess: {exc}")
            raise ValueError(exc)

        return StateMessage(
            stage=stage_name,
            response=txt,
            success=(exc is None),
            statusCode=(200 if exc is None else 500),
            errorMessage=exc,
            response_id=response_id,
            model_version=model_version
        )

class SkeletonAgentPipeline(AgentPipeline):
    class Planner(AgentBasement, prompt=SkeletonAgentRole.PLANNER, input_format=SkeletonAgentInputs.PLANNER):
        def augment_dataset(self, ss: AgentDataset) -> Any: return ss.profiler

        def postprocess(self, response: Any):
            """ Parses the planner response to list form with json. """

            output = get_response(self, response, "planner")
            m = re.search(r"\{.*\}", output.response, flags=re.S)
            obj = json.loads(m.group(0))  # 2) convert to dict
            if not obj.get("steps", None):
                raise ValueError("No steps found in planner response.")

            output.whisper_response = obj

            return output

        def preprocess(self, profiler: AgentDataset, **kwargs):
            if "objective" not in kwargs:
                raise ValueError("Missing 'objective' in kwargs for Planner preprocessing.")

            return {"dataset_schema": profiler.profiler, "objective": kwargs.get("objective")}

    class Executioner(AgentBasement, prompt=SkeletonAgentRole.EXECUTOR, input_format=SkeletonAgentInputs.EXECUTOR):
        def preprocess(self, profiler: AgentDataset, **kwargs):
            """ Prepares the inputs for requesting code block execution. """

            if "current_step" not in kwargs:
                raise ValueError("Missing 'current_step' in kwargs for Executioner preprocessing.")

            return {"dataset_schema": profiler.profiler, "current_step": kwargs.get("current_step")}

        def postprocess(self, response: Any):
            """ Retrieves the code block from LLM and execute via sys function. """
            return get_response(self, response, "executor")

    class Evaluator(AgentBasement, prompt=SkeletonAgentRole.EVALUATOR, input_format=SkeletonAgentInputs.EVALUATOR):
        def postprocess(self, response: Any): return get_response(self, response, "evaluator")

        def preprocess(self, profiler: AgentDataset, **kwargs):
            if "results" not in kwargs or not isinstance(kwargs.get("results"), list):
                raise ValueError("Missing 'results' in kwargs for Evaluator preprocessing.")

            return {"dataset_schema": profiler.profiler, "results": kwargs.get("results")}

    def execute_pipeline(self, current_objective: str, llm: GoogleGenAIProvider, dataset: AgentDataset, **kwargs) -> dict:
        """ Generic Skeleton Agent Cycle to run through all stages sequentially. """

        try:
            traces = {}

            for stage_name, stage_obj in self.items():
                logger.info(f"Starting stage: {stage_name}")

                if stage_name == "planner":
                    state: StateMessage = stage_obj(llm=llm, dataset=dataset, objective=current_objective, **kwargs)
                    logger.info(f"Planner output: {state.response}")

                elif stage_name == "executor":

                    exc_traces = []
                    for step in traces["planner"].whisper_response.get("steps", []):
                        logger.info(f"Executing step: {step}")
                        step_state: StateMessage = stage_obj(llm=llm, dataset=dataset, current_step=step, **kwargs)
                        logger.info(f"Executor output: {step_state.response}")
                        exc_traces.append(step_state)

                    state = exc_traces

                elif stage_name == "evaluator":
                    state: StateMessage = stage_obj(llm=llm, dataset=dataset, results=traces["executor"], **kwargs)
                    evaluation = state.response
                    logger.info(f"Evaluator output: {evaluation}")

                traces[stage_name] = state

            return traces

        except Exception as e:
            logger.exception(f"Error in skeleton_base_cycle: {e}")
            raise e

class DataDiscovery(AgentPipeline):
    class Profiler(AgentBasement, prompt=DataAgentRoleConfig.profiler, input_format=DataAgentInputsTemplate.profiler):
        def preprocess(self, session: AgentDataset):
            return {"data_profile": session.profiler, "data_sample": session.ds.head(5).to_string(index=False)}

        def postprocess(self, response: Any):
            """ Updates the session with profiler results. """
            return get_response(self, response, "profiler")

    def execute_pipeline(self, llm: GoogleGenAIProvider, session: AgentDataset, skele: SkeletonAgentPipeline, **kwargs):
        outputs = []
        traces = []

        try:
            for stage, task in self.items():
                logger.info(f"Starting stage: {stage}")

                output, session = task.execute_pipeline(llm=llm, session=session, **kwargs)
                kwargs.update({"objective": output.whisper_response})
                cycle_output = skele.execute_pipeline(llm=llm, session=session, **kwargs)

                outputs.append(output)
                traces.append(cycle_output)

        except Exception as e:
            logger.exception(f"Error in Data Discovery pipeline: {e}")
            raise e
        finally:
            return outputs, traces, session

class DataModeller(AgentPipeline):
    class DetectNestedDataset(AgentBasement, prompt=DataAgentRoleConfig.modeller, input_format=DataAgentInputsTemplate.modeller):
        def preprocess(self, **kwargs): pass
        def postprocess(self, response: Any): pass
        def augment_dataset(self, ss: AgentDataset) -> Any: pass

    def execute_pipeline(self, llm: GoogleGenAIProvider, *args, **kwargs):
        return super().execute_pipeline(llm, *args, **kwargs)

class DataTransformer(AgentPipeline):
    class MissingDataset(AgentBasement, prompt=DataAgentRoleConfig.MissingValuesHandling, input_format=DataAgentInputsTemplate.MissingValuesHandling):
        def preprocess(self, **kwargs): pass
        def postprocess(self, response: Any): pass
        def augment_dataset(self, ss: AgentDataset) -> Any: pass

    class DeduplicateDataset(AgentBasement, prompt=DataAgentRoleConfig.Deduplication, input_format=DataAgentInputsTemplate.Deduplication):
        def preprocess(self, **kwargs): pass
        def postprocess(self, response: Any): pass
        def augment_dataset(self, ss: AgentDataset) -> Any: pass

    class OutlierDetection(AgentBasement, prompt=DataAgentRoleConfig.OutlierDetection, input_format=DataAgentInputsTemplate.OutlierDetection):
        def preprocess(self, **kwargs): pass
        def postprocess(self, response: Any): pass
        def augment_dataset(self, ss: AgentDataset) -> Any: pass

    def execute_pipeline(self, llm: GoogleGenAIProvider, *args, **kwargs):
        return super().execute_pipeline(llm, *args, **kwargs)

class SessionController(AgentPipeline):
    discovery: DataDiscovery
    modeller: DataModeller

    def __init__(self, dataset: pd.DataFrame, **kwargs):
        self.session = AgentDataset(ds=dataset)
        self.skeleton = SkeletonAgentPipeline()
        self.llm = GoogleGenAIProvider(**kwargs)
        self.agent = AgentCortex()
        self.traces = []

    def execute_pipeline(self, **kwargs):
        """ Executes the full session pipeline. """

        for stage_name, stage in self.items():
            logger.info(f"Starting stage: {stage_name}")
            state, traces, self.session = stage.execute_pipeline(llm=self.llm, session=self.session, skele=self.skeleton, **kwargs)

            self.traces.append({"stage": stage_name, "state": state, "traces": traces})
            self.agent.update(state, fieldPattern=stage_name) # type: ignore

        logger.info(f"Session {self.session.id} completed.")


import pytest
from unittest.mock import MagicMock, patch

@pytest.fixture
def mock_llm(mocker):
    """Mock GoogleGenAIProvider with genai.Client patched."""
    mock_client = MagicMock()
    mocker.patch("app.src.agent.hostess.genai.Client", return_value=mock_client)
    provider = GoogleGenAIProvider(model_id="fake-model", api_key="fake-key")
    mock_client.models.generate_content.return_value = '{"steps": ["Step 1", "Step 2"]}'
    return provider

@pytest.fixture(name="session")
def mock_session():
    """ Provides a demo dataset for testing. """
    data_path = "mock_cafe_sales_dirty.csv"
    df = pd.read_csv(data_path)
    session = SessionController(dataset=df)
    return session

def test_planner_stage_success(mock_llm, mock_session):
    pipeline = SkeletonAgentPipeline()
    response = MagicMock()
    response.model_version = "v1"
    response.response_id = "id123"
    response.extract_text_from_response.return_value = 'Planner response with {"steps": ["Step 1", "Step 2"]}'

    result = pipeline["Planner"](llm=mock_llm, dataset=mock_session, objective="Test objective")

    assert result.success is True
    assert result.whisper_response["steps"] == ["Step 1", "Step 2"]
