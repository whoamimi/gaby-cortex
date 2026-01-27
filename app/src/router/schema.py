# app/src/schema.py

from enum import Enum
from uuid import UUID, uuid4
from datetime import datetime
from fastapi import Depends, Request
from pydantic import BaseModel, Field
from typing import Annotated

demoInput = {
    "id": "demo-testing-id",
    "filename": "demo.csv",
    "dataType": "demo-data",
    "databaseType": "demo-db",
    "dataPlatformType": "demo-platform",
}

RESPONSE_STREAM_TEMPLATE = """
--
Timestamp:  {timestamp}
SESSION ID: {sessionId}
EVENT ID:   {eventId}
STATUS:     {statusCode}
STAGE:      {stage}
CONTENT:
{content}
--
"""

class Templates(Enum):
    idleSession = "[IDLE]"
    startSession = "[START]"
    endSession = "[END]"
    errorStage = "[ERROR]"
    contentStream = """Processing {current} / {total} stage: {stage} ..."""
    responseStream = RESPONSE_STREAM_TEMPLATE.strip()

class SessionInput(BaseModel):
    id: str | UUID = Field(
        description="Unique session identifier",
    )
    timestamp: str | datetime = Field(
        init=False,
        default_factory=datetime.utcnow,
        description="Timestamp of session creation",
    )
    filename: str = Field(
        default=demoInput["filename"],
        description="Input file name",
        examples=[demoInput["filename"]]
    )
    dataType: str = Field(
        description="Data type",
        examples=[demoInput["dataType"]],
        default=demoInput["dataType"]
    ) # type: ignore
    databaseType: str = Field(
        description="Database type",
        examples=[demoInput["databaseType"]],
        default=demoInput["databaseType"]
    )
    dataPlatformType: str = Field(
        description="Data platform type",
        examples=[demoInput["dataPlatformType"]],
        default=demoInput["dataPlatformType"]
    )

class EventOutput(BaseModel):
    content: str
    sessionId: str
    statusCode: int | None = None
    errorMessage: str | None = None
    stage: str = Templates.idleSession.value
    eventId: str | UUID = Field(init=False, default_factory=lambda: uuid4().hex)
    eventTimestamp: str | datetime = Field(init=False, default_factory=datetime.utcnow)

    @property
    def event_response(self):
        return Templates.responseStream.value.format(
            timestamp=self.eventTimestamp,
            sessionId=self.sessionId,
            eventId=self.eventId,
            content=self.content,
            stage=self.stage,
            statusCode=self.statusCode,
        )

async def process_request_inputs(request: Request):
    """ Fetches Headers & Body from incoming request (type Request) and combines into SessionInput model. """

    # sessionId: str | UUID = request.path_params.get("id", "demo-testing-id")
    sessionId = request.headers.get("x-session-id", "demo-testing-id")

    merged: dict = {}
    qp = request.query_params

    for param, default_val in demoInput.items():
        merged[param] = qp.get(param, default_val)

    if merged:
        merged.update({"id": sessionId})
        return SessionInput(**merged)

StreamRequiter = Annotated[SessionInput, Depends(process_request_inputs)]