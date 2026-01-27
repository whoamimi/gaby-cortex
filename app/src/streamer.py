# app/src/streamer.py

import asyncio
from typing import AsyncGenerator

from .router.schema import (
    SessionInput,
    Templates,
    demoInput,
    EventOutput
)

from ..utils.on_startup import get_workspace
from ..utils.woodlogs import setup_logger

logger = setup_logger(__name__)
workspace = get_workspace()

def check_demo_mode(inputs: SessionInput) -> bool:
    demo = SessionInput(**demoInput)

    return (
        inputs.filename == demo.filename
        and inputs.dataType == demo.dataType
        and inputs.databaseType == demo.databaseType
        and inputs.dataPlatformType == demo.dataPlatformType
    )

async def generate_events(inputs: SessionInput) -> AsyncGenerator[bytes, None]:
    """ Asynchronous generator that yields event responses based on the processing stages defined in the workspace configuration."""

    status_code = 200
    error_message = None
    stage = content = Templates.startSession.value

    pipeline_stages = workspace.socket.eventStages
    pipeline_stages_total = len(pipeline_stages)

    try:

        if check_demo_mode(inputs):
            logger.info("Demo mode activated. Running demo pipeline now. ")

        if pipeline_stages_total == 0:
            raise ValueError("No pipeline stages defined in workspace configuration.")

        for idx, stage in enumerate(pipeline_stages):
            # TODO: Simulate processing for each stage / Workflow code here

            event = EventOutput(
                sessionId=str(inputs.id), # pyright: ignore[reportArgumentType]
                content=f"Processing {idx+1} / {pipeline_stages_total} stage: {stage}",
                stage=stage,
                statusCode=status_code,
                errorMessage=error_message,
            )
            logger.debug(f"Generated event: {event}\n")

            yield event.event_response.encode("utf-8")
            await asyncio.sleep(0.5)  # simulate work between updates[web:72][web:81]

        stage = content = Templates.endSession.value

    except Exception as e:
        if isinstance(e, asyncio.CancelledError):
            logger.error(f"Streaming cancelled by Client for session ID: {inputs.id}")
            status_code = 499  # Client Closed Request
        else:
            logger.error(f"Error during event generation for session ID: {inputs.id}: {str(e)}")
            status_code = 500  # Internal Server Error

        error_message = str(e)
        stage = content = Templates.errorStage.value

    finally:
        yield EventOutput(
                sessionId=inputs.id, # pyright: ignore[reportArgumentType]
                content=content,
                stage=stage,
                statusCode=status_code,
                errorMessage=error_message
            ).event_response.encode("utf-8")

