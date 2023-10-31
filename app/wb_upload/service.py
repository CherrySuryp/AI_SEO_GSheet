import json
import sys

import requests

sys.path.append("..")
from app.config import config  # noqa


class Wilderries:
    def __init__(self):
        self._auth = {"Authorization": config.WILDBERRIES_TOKEN}

    def get_all_items(self):
        data = {
            "sort": {
                "cursor": {
                    "limit": 1000
                },
                "filter": {
                    "withPhoto": -1
                }
            }
        }
        req = requests.post(
            "https://suppliers-api.wildberries.ru/content/v1/cards/cursor/list",
            headers=self._auth,
            json=data
        )
        return req.json()

    def get_item_data(self, wb_sku: str | int):
        items = self.get_all_items()["data"]["cards"]
        vendor_code = None
        for item in items:
            if int(wb_sku) == item["nmID"]:
                vendor_code = item["vendorCode"]
                break

        if vendor_code:
            req = requests.post(
                "https://suppliers-api.wildberries.ru/content/v1/cards/filter",
                headers=self._auth,
                json={
                    "vendorCodes": [
                        vendor_code
                    ],
                    "allowedCategoriesOnly": True
                }
            )
            json.dump(req.json(), open("item.json", "w"), ensure_ascii=False, indent=2)


Wilderries().get_item_data("184026386")
