""" app/src/agent/workflow.py

Workflow definitions for data agents.
"""

from typing import Any, Callable
from .base import AgentBasement, AgentPipeline, AgentDataset
from .types import DataAgentRoleConfig, DataAgentInputsTemplate
from .hostess import GoogleGenAIProvider

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
