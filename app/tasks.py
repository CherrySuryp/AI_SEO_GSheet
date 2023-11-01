import random
import time
from typing import Literal

import sentry_sdk
import requests

from wb_upload.service import WildberriesAPI
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
    def req_data_task(mode: Literal["v1", "v1.2", "by_name"], auto_mode: str, wb_sku: int | str, row_id: int):
        try:
            result = requests.post(
                f"http://{Config().PARSER_PATH}/{wb_sku}",
                params={"mode": mode, "wb_sku": wb_sku},
                headers={"x-api-key": Config().PARSER_KEY},
            )
            while True:
                time.sleep(2)

                task_id = result.json()["task_id"]
                check = requests.get(
                    f"http://{Config().PARSER_PATH}/{task_id}/result", headers={"x-api-key": Config().GPT_KEY}
                )
                if result.status_code != 200 or check.status_code != 200:
                    print(f"exc {row_id}")
                    Worker.gsheet.update_cell(
                        "Произошла ошибка сбора данных. " "Скорее всего все сработает если попробовать еще раз.",
                        f"K{row_id}",
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
            Worker.gsheet.update_cell("", f"K{row_id}")
        else:
            Worker.gsheet.update_status("Сгенерировать описание", row_id)
            Worker.gsheet.update_cell("", f"K{row_id}")

    @staticmethod
    @celery.task(soft_time_limit=180, time_limit=240)
    def chatgpt_task(prompt: str, row_id: int) -> None:
        try:
            time.sleep(random.randint(1, 5))
            result = requests.post(
                f"http://{Config().GPT_PATH}/gpt", params={"prompt": prompt}, headers={"x-api-key": Config().GPT_KEY}
            )
            while True:
                time.sleep(2)

                task_id = result.json()["task_id"]
                check = requests.get(
                    f"http://{Config().GPT_PATH}/{task_id}/result", headers={"x-api-key": Config().GPT_KEY}
                )
                if check.status_code == 500:
                    Worker.gsheet.update_cell(
                        "Произошла ошибка генерации текста. " "Скорее всего все сработает если попробовать еще раз.",
                        f"K{row_id}",
                    )
                    Worker.gsheet.update_status("ОШИБКА", row_id)
                    break

                if check.json()["status"] == "SUCCESS":
                    result = check.json()["result"]

                    # Записываем результат в таблицу
                    Worker.gsheet.update_status("Завершено", row_id)
                    Worker.gsheet.update_cell("", f"L{row_id}")
                    Worker.gsheet.update_cell(result, f"J{row_id}")
                    break
        except Exception as e:
            print(e)
            sentry_sdk.capture_exception(e)

    @staticmethod
    @celery.task(time_limit=60)
    def upload_to_wb_task(wb_sku: str | int, desc: str, row_id: int) -> None:
        wb_api = WildberriesAPI()
        item_data = wb_api.get_item_data(wb_sku)

        if item_data:
            item_data[-1]["characteristics"][-1]["Описание"] = desc
            wb_api.update_description(item_data)
        else:
            Worker.gsheet.update_cell(
                "Не удалось обновить описание. Товар не найден или не принадлежит Вам. Убедитесь что верно ввели SKU.",
                f"K{row_id}",
            )
            Worker.gsheet.update_status("ОШИБКА", row_id)
