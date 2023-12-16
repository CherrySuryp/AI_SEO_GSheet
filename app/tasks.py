import random
import time
from typing import Literal

import sentry_sdk
import requests

from app.wb_upload.service import WildberriesAPI
from app.gsheets.service import GSheet
from app.utils.service import TextUtils
from app.config import Config
from app.queue import celery

config = Config()


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
                        f"L{row_id}",
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
    def gpt_generate_description_task(prompt: str, row_id: int) -> None:
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
                        f"L{row_id}",
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
    @celery.task(soft_time_limit=180, time_limit=240)
    def gpt_check_keywords_in_desc_task(prompt: str, row_id: int) -> None:
        try:
            result = requests.post(
                f"http://{config.GPT_PATH}/gpt",
                params={"prompt": prompt, "model": "gpt-3.5-turbo"},
                headers={"x-api-key": config.GPT_KEY}
            )
            while True:
                time.sleep(2)

                task_id = result.json()["task_id"]
                check = requests.get(
                    f"http://{config.GPT_PATH}/{task_id}/result", headers={"x-api-key": Config().GPT_KEY}
                )
                if check.status_code == 500:
                    Worker.gsheet.update_cell(
                        "Произошла ошибка генерации текста. " "Скорее всего все сработает если попробовать еще раз.",
                        f"L{row_id}",
                    )
                    Worker.gsheet.update_status("ОШИБКА", row_id)
                    break
                if check.json()["status"] == "SUCCESS":
                    result = check.json()["result"]

                    # Записываем результат в таблицу
                    Worker.gsheet.update_status("Завершено", row_id)
                    Worker.gsheet.update_cell("", f"L{row_id}")
                    Worker.gsheet.update_cell(result, f"K{row_id}")
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
            Worker.gsheet.update_status("Завершено", row_id)
        else:
            Worker.gsheet.update_cell(
                "Не удалось обновить описание. Товар не найден или не принадлежит Вам. Убедитесь что верно ввели SKU.",
                f"L{row_id}",
            )
            Worker.gsheet.update_status("ОШИБКА", row_id)
