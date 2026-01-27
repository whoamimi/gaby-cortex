# app/utils/exceptions.py

from fastapi.responses import JSONResponse

async def validation_exception_handler(request, exc):
    print("Validation error:", exc.errors())
    return JSONResponse(status_code=422, content={"detail": exc.errors()})