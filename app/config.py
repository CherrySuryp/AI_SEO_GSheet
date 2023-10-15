import os
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

dir_path = os.path.dirname(os.path.realpath(__file__))


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=os.path.join(dir_path, "../.env"), env_file_encoding="utf-8")

    MODE: Literal["DEV", "PROD"]

    USE_SENTRY: Literal["TRUE", "FALSE"]
    SENTRY_DSN: str

    GPT_PATH: str
    GPT_KEY: str
    PARSER_PATH: str
    PARSER_KEY: str

    REFRESH_INTERVAL: int
    GSHEET_ID: str
    GOOGLE_CREDS: str


settings = Config()

if Config().MODE == "PROD":
    REDIS_URL = "redis://redis_ai_seo_gsheet:6379/0"

else:
    REDIS_URL = "redis://127.0.0.1:6379/0"
    Config().GPT_PATH = "91.206.15.62:8000"
    Config().PARSER_PATH = "91.206.15.62:9000"
