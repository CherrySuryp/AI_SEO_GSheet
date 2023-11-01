import re
import asyncio
from datetime import datetime

from gsheets.service import GSheet
from utils.service import TextUtils
from config import Config
from tasks import Worker


class TaskService:
    def __init__(self):
        self.settings = Config()
        self.send_task = Worker()
        self.gsheet = GSheet()
        self.utils = TextUtils()

    async def fetcher_worker(self) -> None:
        """
        Опрос таблицы каждые N секунд и отправка новых задач в очередь
        """
        print(f"{datetime.now().replace(microsecond=0)}: Program has started")

        while True:
            await asyncio.sleep(self.settings.REFRESH_INTERVAL)  # интервал между опросами таблицы
            try:
                sheet_data = self.gsheet.read_sheet()  # чтение таблицы

                for i in range(len(sheet_data)):
                    row_id = i + 2
                    task_status: str = sheet_data[i][0]
                    work_mode: str = sheet_data[i][1]
                    auto_mode: str = sheet_data[i][2]
                    log = None

                    if task_status == "Собрать ключи":
                        """
                        Сборка данных
                        """
                        if work_mode == "По названию товара":
                            wb_sku = sheet_data[i][3]
                            if wb_sku:
                                log = 1
                                self.gsheet.update_status("В работе", row_id)
                                self.gsheet.update_cell("", f"L{row_id}")
                                self.send_task.req_data_task.delay(
                                    mode="by_name", auto_mode=auto_mode, wb_sku=wb_sku, row_id=row_id
                                )
                            else:
                                self.gsheet.update_cell("Недостаточно данных: название товара", f"L{row_id}")
                                self.gsheet.update_status("ОШИБКА", row_id)

                        elif work_mode == "Со сборкой ключей V1.0":
                            wb_sku = int(re.search(r"\d+", sheet_data[i][3]).group()) if sheet_data[i][3] else None
                            if wb_sku:
                                log = 1
                                self.gsheet.update_status("В работе", row_id)
                                self.gsheet.update_cell("", f"L{row_id}")
                                self.send_task.req_data_task.delay(
                                    mode="v1", auto_mode=auto_mode, wb_sku=wb_sku, row_id=row_id
                                )
                            else:
                                self.gsheet.update_cell("Недостаточно данных: SKU или ссылка на товар", f"L{row_id}")
                                self.gsheet.update_status("ОШИБКА", row_id)

                        elif work_mode == "Со сборкой ключей V1.2":
                            wb_sku = int(re.search(r"\d+", sheet_data[i][3]).group()) if sheet_data[i][3] else None
                            if wb_sku:
                                log = 1
                                self.gsheet.update_status("В работе", row_id)
                                self.gsheet.update_cell("", f"L{row_id}")
                                self.send_task.req_data_task.delay(
                                    mode="v1.2", auto_mode=auto_mode, wb_sku=wb_sku, row_id=row_id
                                )
                            else:
                                self.gsheet.update_cell("Недостаточно данных: SKU или ссылка на товар", f"L{row_id}")
                                self.gsheet.update_status("ОШИБКА", row_id)

                    if task_status == "Сгенерировать описание":
                        """
                        Генерация описания
                        """
                        log = 1
                        prompt = self.utils.row_to_ai_prompt(sheet_data[i])
                        self.gsheet.update_status("В работе", row_id)
                        self.send_task.chatgpt_task.delay(prompt=prompt, row_id=row_id)

                    if task_status == "Выгрузить на ВБ":
                        """
                        Обновление информации в ЛК продавца
                        """
                        try:
                            wb_sku = int(re.search(r"\d+", sheet_data[i][3]).group()) if sheet_data[i][3]
                            desc = sheet_data[i][9]
                        except IndexError:
                            wb_sku = None
                            desc = None

                        if not desc:
                            Worker.gsheet.update_cell("Нет описания", f"K{row_id}")
                            Worker.gsheet.update_status("ОШИБКА", row_id)
                        elif not wb_sku:
                            Worker.gsheet.update_cell("Нет SKU", f"K{row_id}")
                            Worker.gsheet.update_status("ОШИБКА", row_id)
                        else:
                            self.gsheet.update_status("В работе", row_id)
                            self.send_task.upload_to_wb_task.delay(wb_sku=wb_sku, desc=desc, row_id=row_id)
                    if log:
                        print(f"{datetime.now().replace(microsecond=0)}:" f" Sent task from row {row_id} to queue")
            except Exception as ex:
                print(ex)
                await asyncio.sleep(self.settings.REFRESH_INTERVAL / 2)
