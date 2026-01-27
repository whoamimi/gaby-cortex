# test_app.py
# TODO

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.src.router.schema import EventOutput, demoInput

demo_output_true = [
    EventOutput(
        sessionId=demoInput["id"],
        content="Processing [IDLE] ...",
        statusCode=200,
        errorMessage=None,
    ),
    EventOutput(
        sessionId=demoInput["id"],
        content="Processing 1 / 3 stage: ingest ...",
        stage="ingest",
        statusCode=200,
        errorMessage=None,
    )
]

@pytest.mark.anyio
async def test_sse_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport) as client:
        # Use client.stream() to handle the streaming response
        async with client.stream("GET", "/stream") as response:
            assert response.status_code == 200
            # Read and process the streamed content
            content = await response.read() # type: ignore
            # The content will be a single string containing all events
            # You will need to parse it according to the SSE format (data: ...\n\n)
            expected_content = 'data: {"data": "message 1"}\n\ndata: {"data": "message 2"}\n\n'
            assert content.decode() == expected_content