# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

import pymongo

from scrapy.conf import settings
from pymongo import MongoClient
from BusCrawl.items.bus100 import LineItem


class MongoBus100Pipeline(object):
    def open_spider(self, spider):
        db_config = settings.get("MONGODB_CONFIG")
        self.client = MongoClient(db_config["url"])
        self.db = self.client[db_config["db"]]

        line_pks = [
            ("line_id", pymongo.ASCENDING)
        ]
        self.db.line_bus100.create_index(line_pks, unique=True)

    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):
        if not spider.name == "bus100":
            return
        if isinstance(item, LineItem):
            query = {
                    "line_id": item["line_id"],
                   }
            self.db.line_bus100.update(query, {"$set": dict(item)}, upsert=True)
        return item
