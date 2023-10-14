#!/usr/bin/env python
import asyncio

from config import Config
from service import TaskService

import logging
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration


def sentry_logs() -> None:
    settings = Config()

    if settings.MODE == "PROD" and settings.USE_SENTRY == "TRUE":
        sentry_logging = LoggingIntegration(level=logging.INFO, event_level=logging.ERROR)
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            traces_sample_rate=1.0,
            integrations=[sentry_logging],
        )


def main() -> None:
    loop = asyncio.get_event_loop()
    loop.run_until_complete(TaskService().fetcher_worker())


if __name__ == "__main__":
    sentry_logs()
    main()
