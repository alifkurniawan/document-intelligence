"""Local PyCharm and command-line entry point for the API."""

import uvicorn

from app.api.app import app
from app.core.config import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)


if __name__ == "__main__":
    main()
