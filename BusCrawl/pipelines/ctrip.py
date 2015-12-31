# -*- coding: utf-8 -*-

import pymongo

from scrapy.conf import settings
from pymongo import MongoClient
from BusCrawl.items.ctrip import LineItem

class MongoPipeline(object):
    def open_spider(self, spider):
        db_config = settings.get("MONGODB_CONFIG")
        self.client = MongoClient(db_config["url"])
        self.db = self.client[db_config["db"]]

        line_pks = [
            ("line_id", pymongo.ASCENDING),
            ("drv_datetime", pymongo.ASCENDING),
        ]
        self.db.ctrip_line.create_index(line_pks, unique=True)

    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):
        pk = {
            "line_id": item["line_id"],
        }
        self.db.ctrip_line.replace_one(pk, dict(item), upsert=True)
