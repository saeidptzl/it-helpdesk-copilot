"""Run the web server: `python -m app` (host and port come from HOST and PORT)."""

import uvicorn

from .config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, log_level="info")
