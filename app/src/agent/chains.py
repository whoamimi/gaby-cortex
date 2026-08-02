from abc import abstractmethod
import sys
from pathlib import Path

import re
import json
import pandas as pd
from typing import Any, OrderedDict

# from app.src.agent.rl import AgentCortex
from app.src.agent.hostess import GoogleGenAIProvider
from app.src.agent.base import AgentDataset, StateMessage, AgentBasement, AgentPipeline
from app.src.agent.types import (
    DataAgentInputsTemplate,
    DataAgentRoleConfig,
    SkeletonAgentInputs,
    SkeletonAgentRole,
)

BACKEND = Path("/Users/mimiphan/mimeus-app/databy-ai/backend").resolve()
assert (
    BACKEND / "app"
).is_dir(), f"Expected app/ under {BACKEND}, but it wasn't found."

# Put BACKEND first
if str(BACKEND) in sys.path:
    sys.path.remove(str(BACKEND))
sys.path.insert(0, str(BACKEND))

# Purge any previously imported wrong 'app'
for k in list(sys.modules.keys()):
    if k == "app" or k.startswith("app."):
        del sys.modules[k]


from app.utils.woodlogs import setup_logger

logger = setup_logger(__name__)

_JSON_OBJ = re.compile(r"\{.*\}", re.S)
_CODE_FENCE_PYTHON_RE = re.compile(
    r"```(?:python)?\s*(.*?)```", re.DOTALL | re.IGNORECASE
)
_CODE_FENCE_JSON_RE = re.compile(
    r"```json\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE
)


def get_response(obj, response: Any, stage_name: str = "planner") -> StateMessage:
    """Generic response formatter for Skeleton Agent stages."""

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
            model_version=model_version,
        )


def extract_first_json_obj(text: str) -> dict:
    """Extracts the first {...} blob and parses JSON; raises cleanly if absent/invalid."""
    m = _CODE_FENCE_JSON_RE.search(text)
    if not m:
        raise ValueError("No JSON object found in model response.")
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in model response: {e}") from e


class SkeletonAgentPipeline(AgentPipeline):
    class Planner(
        AgentBasement,
        prompt=SkeletonAgentRole.PLANNER,
        input_format=SkeletonAgentInputs.PLANNER,
    ):
        def postprocess(self, response: Any):
            """Parses the planner response to list form with json.

            Args:
                response (Any): The raw response from the LLM.
            Returns:
                StateMessage: The processed state message with parsed steps.
            """
            try:
                output = get_response(self, response, "planner")
                obj = extract_first_json_obj(output.response)

                if (
                    not isinstance(obj, dict)
                    or "steps" not in obj
                    or not isinstance(obj["steps"], list)
                ):
                    raise ValueError(
                        "Planner response JSON must contain a 'steps' key with a list of steps."
                    )

                output.whisper_response = obj
            except Exception as e:
                logger.error(f"Error in Planner postprocess: {e}")
                output.success = False
                output.errorMessage = "Problem postprocessing at Planner:" + str(e)

            return output

        def preprocess(self, dataset: AgentDataset, inputs, **kwargs):
            """Prepares the inputs for requesting plan generation.

            Args:
                dataset (AgentDataset): The dataset context.
                inputs (dict): The input parameters.
            Returns:
                dict: The formatted inputs for the planner.

            """
            if "objective" not in inputs:
                raise ValueError(
                    "Missing 'objective' in inputs for Planner preprocessing."
                )

            return {
                "dataset_schema": dataset.profiler,
                "objective": inputs.get("objective"),
            }

    class Executioner(
        AgentBasement,
        prompt=SkeletonAgentRole.EXECUTOR,
        input_format=SkeletonAgentInputs.EXECUTOR,
    ):
        def preprocess(self, dataset: AgentDataset, inputs, **kwargs):
            """Prepares the inputs for requesting code block execution."""

            if "current_step" not in inputs:
                raise ValueError(
                    "Missing 'current_step' in inputs for Executioner preprocessing."
                )

            return {
                "dataset_schema": dataset.profiler,
                "current_step": inputs.get("current_step"),
            }

        def postprocess(self, response: Any):
            """Retrieves the code block from LLM and execute via sys function. TODO: EXECUTE SCRIPT SAFELY."""
            script_code = get_response(self, response, "executor")
            # 1) PARSE AND EXTRACT CODE BLOCK
            # 2) EXECUTE CODE SAFELY HERE
            # 3) CAPTURE OUTPUT IN ./TMP FOLDER AND RETURN
            return "results"

    class Evaluator(
        AgentBasement,
        prompt=SkeletonAgentRole.EVALUATOR,
        input_format=SkeletonAgentInputs.EVALUATOR,
    ):
        def preprocess(self, dataset: AgentDataset, inputs, **kwargs):
            if "results" not in inputs or not isinstance(inputs.get("results"), list):
                raise ValueError(
                    "Missing 'results' in inputs for Evaluator preprocessing."
                )

            return {
                "dataset_schema": dataset.profiler,
                "results": inputs.get("results"),
            }

        @abstractmethod
        def postprocess(self, response: Any) -> StateMessage:
            # TODO: Immediately prompts reflection task to clean up code execution artifacts.
            return get_response(self, response, "evaluator")

    @abstractmethod
    def execute_pipeline(
        self, inputs: dict, llm: GoogleGenAIProvider, dataset: AgentDataset, **kwargs
    ) -> dict:
        """One pass: planner -> executor steps -> evaluator."""
        traces = {}

        prev = inputs.copy()
        for stage, stager in self.items():
            if stage not in traces:
                traces[stage] = []

            if stage == "executor":
                substep = []
                for step in prev.whisper_response.get("steps", []):  # type: ignore
                    state: StateMessage = stager(
                        llm=llm,
                        dataset=dataset,
                        inputs={"current_step": step},
                        **kwargs,
                    )
                    substep.append(state)

                    print(f"[{stage.upper()}] Step: {step} State: {state}")
                traces[stage].extend(substep)
                prev = state

            else:
                state: StateMessage = stager(
                    llm=llm, dataset=dataset, inputs=prev, **kwargs
                )
                traces[stage].append(state)
                prev = state
                print(f"[{stage.upper()}] State: {state}")

        return traces


def execute_cycle(
    self: AgentPipeline,
    llm: GoogleGenAIProvider,
    dataset: AgentDataset,
    skele: SkeletonAgentPipeline,
    inputs: dict,
    **kwargs,
):
    traces = {}

    try:
        for stage, task in self.items():
            logger.info(f"Starting stage: {stage}")

            if stage not in traces:
                traces[stage] = {}

            traces[stage]["inputs"] = task.preprocess(session=session, **kwargs)
            traces[stage]["cycle_output"] = skele.execute_pipeline(
                inputs=traces[stage]["inputs"], llm=llm, dataset=session, **kwargs
            )
            traces[stage]["outputs"], session = task.postprocess(
                cycle_output=traces[stage]["cycle_output"], session=session
            )

        return traces

    except Exception as e:
        logger.exception(f"Error in Data Discovery pipeline: {e}")
        raise e
    finally:
        return traces, session


class DataDiscovery(AgentPipeline):
    """Data Discovery Pipeline for profiling and initial data assessment.

    Stages:
        1) Profiler: Generates a profile of the dataset.
    """

    class Profiler(
        AgentBasement,
        prompt=DataAgentRoleConfig.profiler,
        input_format=DataAgentInputsTemplate.profiler,
    ):
        def preprocess(self, session: AgentDataset):
            """Prepares the dataset profile and sample for the profiler agent.

            Args:
                session (AgentDataset): The current session dataset.
            Returns:
                str: The formatted input string for the profiler agent.
            """
            return dict(
                data_profile=session.profiler,
                data_sample=session.ds.head(5).to_string(index=False),
                objective=self.prompt,
            )

        def postprocess(self, output: Any):
            """Updates the session with profiler results."""
            try:
                output = get_response(self, output, "profiler")
                if "```html" in output.response:
                    output.response = output.response.strip("```html")
                if "```" in output.response:
                    output.response = output.response.strip("```")

                table = pd.read_html(output.response, header=0)
                table = (
                    table[0]
                    if isinstance(table, list) and len(table) > 0
                    else pd.DataFrame()
                )
                output.whisper_response = table

            except Exception as e:
                logger.error(f"Error in Profiler postprocess: {e}")
                output.success = False
                output.errorMessage = "Problem at:" + str(e)

            return output

    def execute_pipeline(
        self,
        llm: GoogleGenAIProvider,
        session: AgentDataset,
        skele: SkeletonAgentPipeline,
        **kwargs,
    ):
        traces = {}
        try:
            profiler = self["profiler"]
            output, update_ss = profiler(llm=llm, dataset=session, **kwargs)
            traces["profiler"] = output
            return traces, update_ss

        except Exception as e:
            logger.exception(f"Error in Data Discovery pipeline: {e}")
            raise e


class SessionController:
    """Manages the full session lifecycle and orchestrates the agent pipelines.

    Args:
        dataset (pd.DataFrame): The dataset to be processed.
        **kwargs: Additional keyword arguments for LLM provider configuration.

    Examples:
        To Run complete session:
            >>> import pandas as pd
            >>> from app.src.agent.chains import SessionController
            >>> df = pd.read_csv("path/to/dataset.csv")
            >>> ss = SessionController(dataset=df)
            >>> ss.execute_pipeline()
        To access a data stage:
            >>> data_stage = ss.stages["discovery"]
        To access a data stage's stage (substage):
            >>> profiler_stage = ss.stages["discovery"].stages["profiler"]
        To run only data discovery stage:
            >>> data_stage = ss.stages["discovery"]
    """

    def __init__(self, dataset: pd.DataFrame, **kwargs):
        super(SessionController, self).__init__()
        self.session = AgentDataset(ds=dataset)
        self.skeleton = SkeletonAgentPipeline()
        self.llm = GoogleGenAIProvider(**kwargs)
        # self.agent = AgentCortex()
        self.stages = OrderedDict([("discovery", DataDiscovery())])
        self.traces = {}

    def execute_pipeline(self, **kwargs):
        """Orchestrates the full session execution through all pipeline stages.

        Executes the data discovery stage to profile and assess the dataset,
        then proceeds through the skeleton agent pipeline for analysis.

        Args:
            **kwargs: Additional keyword arguments passed to pipeline stages.

        Returns:
            dict: Traces from all executed stages.

        Raises:
            Exception: If any stage execution fails.
        """
        try:
            logger.info("Starting SessionController pipeline execution")

            # Execute discovery stage (profiling)
            discovery = self.stages["discovery"]
            traces_discovery, self.session = discovery.execute_pipeline(
                llm=self.llm, session=self.session, skele=self.skeleton, **kwargs
            )
            self.traces["discovery"] = traces_discovery
            logger.info("Discovery stage completed successfully")

            # Execute skeleton agent pipeline
            traces_skeleton = self.skeleton.execute_pipeline(
                inputs={"objective": kwargs.get("objective", "Analyze dataset")},
                llm=self.llm,
                dataset=self.session,
                **kwargs,
            )
            self.traces["skeleton"] = traces_skeleton
            logger.info("Skeleton agent pipeline completed successfully")

            return self.traces

        except Exception as e:
            logger.exception(f"Error in SessionController pipeline execution: {e}")
            raise e


if __name__ == "__main__":
    logger.debug("Agent Chains module loaded.")

    import pandas as pd
    from pathlib import Path

    if Path("mock_cafe_sales_dirty.csv").exists():
        data_path = "mock_cafe_sales_dirty.csv"
    else:
        data_path = Path("../../..").resolve() / "mock_cafe_sales_dirty.csv"
        logger.debug(f"Data path resolved to: {data_path}")

    df = pd.read_csv(data_path)
    logger.debug(f"Data loaded with shape: {df.shape}")
    ss = SessionController(dataset=df)
    logger.debug(
        f"SessionController initialized with Data Stages: {list(ss.stages.keys())}"
    )

    discovery = ss.stages["discovery"]
    profiler = discovery["profiler"]
