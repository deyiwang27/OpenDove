import uvicorn

from opendove.api.app import app
from opendove.config import settings
from opendove.logging_config import configure_logging


def main() -> None:
    configure_logging(settings.env)
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
