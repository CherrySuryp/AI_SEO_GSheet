import sys

import requests

sys.path.append("..")
from app.config import config  # noqa


class WildberriesAPI:
    def __init__(self):
        self._auth = {"Authorization": config.WILDBERRIES_TOKEN}

    def _get_all_items(self):
        body = {"sort": {"cursor": {"limit": 1000}, "filter": {"withPhoto": -1}}}
        req = requests.post(
            "https://suppliers-api.wildberries.ru/content/v1/cards/cursor/list",
            headers=self._auth,
            json=body
        )
        return req.json()

    def get_item_data(self, wb_sku: str | int):
        items = self._get_all_items()["data"]["cards"]
        vendor_code = None
        for item in items:
            if int(wb_sku) == item["nmID"]:
                vendor_code = item["vendorCode"]
                break

        if vendor_code:
            body = {"vendorCodes": [vendor_code], "allowedCategoriesOnly": True}
            req = requests.post(
                   "https://suppliers-api.wildberries.ru/content/v1/cards/filter",
                   headers=self._auth,
                   json=body
               )
            return req.json()["data"]

    def update_description(self, params: list):
        req = requests.post(
            "https://suppliers-api.wildberries.ru/content/v1/cards/update",
            headers=self._auth,
            json=params
        )
        print(req)


# wb = WildberriesAPI()
# data = wb.get_item_data("175383876")
# print(data)
# data[-1]["characteristics"][-1]["Описание"] = "Второй тест загрузки описания!"
# wb.update_description(data)
