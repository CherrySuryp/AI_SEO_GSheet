import time
from typing import Literal

import sentry_sdk
import requests

from gsheets.service import GSheet
from utils.service import TextUtils

from config import Config
from celery_app import celery


class Worker:
    """
    Основная бизнес логика программы
    """

    gsheet = GSheet()
    text_utils = TextUtils()

    @staticmethod
    @celery.task(soft_time_limit=120, time_limit=180)
    def get_parsed_data(
            mode: Literal["v1", "v1.2", "by_name"],
            auto_mode: str,
            wb_sku: int | str,
            row_id: int
    ):
        try:
            result = requests.post(
                f"http://91.206.15.62:9000/{wb_sku}",
                params={"mode": mode, "wb_sku": wb_sku},
                headers={"x-api-key": Config().PARSER_KEY}
            )
            while True:
                time.sleep(2)

                task_id = result.json()["task_id"]
                check = requests.get(
                    f"http://91.206.15.62:9000/{task_id}/result",
                    headers={"x-api-key": Config().GPT_KEY}
                )
                if result.status_code != 200 or check.status_code != 200:
                    print(f"exc {row_id}")
                    Worker.gsheet.update_cell(
                        "Произошла ошибка сбора данных. "
                        "Скорее всего все сработает если попробовать еще раз.",
                        f"J{row_id}"
                    )
                    break
                if check.json()["status"] == "SUCCESS":
                    result = check.json()["result"]
                    break

            if mode == "v1":
                Worker.gsheet.update_cell(result["name"], f"E{row_id}")
                Worker.gsheet.update_cell(str(result["params"]), f"F{row_id}")
                Worker.gsheet.update_cell(", ".join(result["keywords"]), f"H{row_id}")

            elif mode == "v1.2":
                Worker.gsheet.update_cell(result["name"], f"E{row_id}")
                Worker.gsheet.update_cell(str(result["params"]), f"F{row_id}")
                Worker.gsheet.update_cell(str(result["desc"]), f"G{row_id}")
                Worker.gsheet.update_cell(", ".join(result["keywords"]), f"H{row_id}")

            elif mode == "by_name":
                Worker.gsheet.update_cell(wb_sku, f"E{row_id}")
                Worker.gsheet.update_cell(", ".join(result["keywords"]), f"H{row_id}")

            print(f"Data written to row {row_id}")
        except Exception as e:
            print(e)
            sentry_sdk.capture_exception(e)

        if auto_mode == "Ручной":
            Worker.gsheet.update_status("Завершено", row_id)
        else:
            Worker.gsheet.update_status("Сгенерировать описание", row_id)

    @staticmethod
    @celery.task(soft_time_limit=180, time_limit=240)
    def chatgpt_task(prompt: str, row_id: int) -> None:
        try:
            result = requests.post(
                f"http://91.206.15.62:8000/gpt",
                params={"prompt": prompt},
                headers={"x-api-key": Config().GPT_KEY}
            )
            while True:
                time.sleep(2)

                task_id = result.json()["task_id"]
                check = requests.get(
                    f"http://91.206.15.62:8000/{task_id}/result",
                    headers={"x-api-key": Config().GPT_KEY}
                )
                if check.status_code == 500:
                    Worker.gsheet.update_cell(
                        "Произошла ошибка генерации текста. "
                        "Скорее всего все сработает если попробовать еще раз.",
                        f"J{row_id}"
                    )
                    break
                if check.json()["status"] == "SUCCESS":
                    result = check.json()["result"]

                    # Записываем результат в таблицу
                    Worker.gsheet.update_status("Завершено", row_id)
                    Worker.gsheet.update_cell(result, f"J{row_id}")
                    break
        except Exception as e:
            sentry_sdk.capture_exception(e)
