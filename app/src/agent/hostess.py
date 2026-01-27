""" app/src/agent/hostess.py

Google GenAI LLM Provider Class.
"""

from google import genai
from google.genai import types
from dataclasses import dataclass
from ... import workspace
from ...utils.woodlogs import setup_logger

logger = setup_logger(__name__)

BASE_GEMINI_MODEL = "gemini-2.5-flash-lite"
DEFAULT_KWARGS = {
    "temperature": 1.1,
    "topP": 0.95,
    "topK": 50,
    "candidateCount": 1,
    "max_output_tokens": 276,

}

@dataclass
class GenAIMessage:
    """ Type definition for Google GenAI LLM message input. """

    content: str
    decoder_kwargs: dict
    system_instruction: str | types.GenerateContentConfigOrDict | None = None
    reference_id: str | None = None

    def __post_init__(self):
        if not isinstance(self.content, str):
            raise ValueError("content must be a string.")

        if self.system_instruction and isinstance(self.system_instruction, str):

            self.system_instruction = types.GenerateContentConfigDict(system_instruction=self.system_instruction, **self.decoder_kwargs)

            if self.reference_id and isinstance(self.reference_id, str):
                self.system_instruction["response_id"] = self.reference_id


class GoogleGenAIProvider:
    """ Google GenAI LLM provider implementation."""

    def __init__(
        self,
        model_id: str = BASE_GEMINI_MODEL,
        api_key: str = workspace.secrets._genai_api_key,
        **kwargs
    ):
        self.model_id = model_id
        self.client = genai.Client(
            api_key=api_key
        )
        self.default = {k: kwargs.get(k, v) for k, v in DEFAULT_KWARGS.items()}

    def __call__(self, msg: GenAIMessage):
        """ Generic Caller for Google GenAI LLMs. """

        response: types.GenerateContentResponse = self.client.models.generate_content(
            model=self.model_id,
            config=msg.system_instruction, # type: ignore
            contents=msg.content,  # type: ignore[arg-type]
        )

        return response

    @staticmethod
    def _extract_text_from_response(response: types.GenerateContentResponse) -> str | None:
        """ Generic postprocess method to extract text from LLM response text only. """

        if (
            response and isinstance(response, types.GenerateContentResponse)
            and isinstance(response.candidates, list) \
                and hasattr(response.candidates[0], "content") and isinstance(response.candidates[0].content, types.Content) \
                    and hasattr(response.candidates[0].content, "parts") and isinstance(response.candidates[0].content.parts, list) \
                        and hasattr(response.candidates[0].content.parts[0], "text") and isinstance(response.candidates[0].content.parts[0].text, str)
        ):
            return response.candidates[0].content.parts[0].text
        else:
            logger.error(f"Unexpected response format: {response}")
            raise ValueError("Error: Unable to retrieve response from Google GenAI.")