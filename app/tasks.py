import time

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
    def parse_wb_item_name(wb_sku: int, row_id: int):
        try:
            item_name = Parser().get_wb_item_name(wb_sku)
            Worker.gsheet.update_cell(content=item_name, row_id=f"E{row_id}")
        except Exception as e:
            sentry_sdk.capture_exception(e)

    @staticmethod
    @celery.task(soft_time_limit=120, time_limit=180)
    def parse_wb_item_params(wb_sku: int, row_id: int):
        try:
            item_params = Parser().get_wb_item_params(wb_sku)
            item_params = TextUtils().exclude_dim_info(item_params)
            Worker.gsheet.update_cell(content=str(item_params), row_id=f"F{row_id}")
        except Exception as e:
            sentry_sdk.capture_exception(e)

    @staticmethod
    @celery.task(soft_time_limit=120, time_limit=180)
    def parse_wb_item_desc(wb_sku: int, row_id: int):
        try:
            item_desc = Parser().get_wb_item_desc(wb_sku)
            Worker.gsheet.update_cell(content=str(item_desc), row_id=f"G{row_id}")
        except Exception as e:
            sentry_sdk.capture_exception(e)

    @staticmethod
    @celery.task(soft_time_limit=120, time_limit=180)
    def parse_mpstats_keywords_by_sku(auto_mode: str, wb_sku: int, row_id: int):
        keywords = None
        try:
            keywords = Parser().parse_mpstats_by_sku(wb_sku)
        except Exception as e:
            sentry_sdk.capture_exception(e)

        keywords = Worker.text_utils.transform_dict_keys_to_str(keywords) if keywords else None
        Worker.gsheet.update_cell(row_id=f"H{row_id}", content=keywords)

        if auto_mode == "Ручной":
            Worker.gsheet.update_status("Завершено", row_id)
        else:
            Worker.gsheet.update_status("Сгенерировать описание", row_id)

    @staticmethod
    @celery.task(soft_time_limit=120, time_limit=180)
    def parse_mpstats_keywords_by_item_name(auto_mode: str, item_name: str, row_id: int):
        keywords = None
        try:
            keywords = Parser().parse_mpstats_by_name(item_name)
        except Exception as e:
            sentry_sdk.capture_exception(e)

        keywords = Worker.text_utils.transform_dict_keys_to_str(keywords) if keywords else None
        Worker.gsheet.update_cell(row_id=f"H{row_id}", content=keywords)

        if auto_mode == "Авто":
            Worker.gsheet.update_status("Сгенерировать описание", row_id)
        else:
            Worker.gsheet.update_status("Завершено", row_id)

    @staticmethod
    @celery.task(soft_time_limit=180, time_limit=240)
    def chatgpt_task(prompt: str, row_id: int) -> None:
        try:
            result = requests.post(
                f"http://localhost:8000/gpt",
                params={"prompt": prompt},
                headers={"x-api-key": Config().GPT_KEY}
            )
            print(result.json())
            while True:
                task_id = result.json()["task_id"]
                check = requests.get(
                    f"http://localhost:8000/{task_id}/result",
                    headers={"x-api-key": Config().GPT_KEY}
                )
                if check.status_code == 500:
                    Worker.gsheet.update_cell(
                        "Произошла ошибка. "
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
                time.sleep(2)
        except Exception as e:
            sentry_sdk.capture_exception(e)


Worker().chatgpt_task.delay(prompt="Привет! Расскажи о себе в двух словах", row_id=2)
