# app/__main__.py

from .utils.on_startup import get_workspace

workspace = get_workspace()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        workspace.app_path,
        host=workspace.app_host,
        port=workspace.app_port,
        reload=workspace.debug_mode,
        log_level="debug" if workspace.debug_mode else "info",
        access_log=workspace.debug_mode,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )