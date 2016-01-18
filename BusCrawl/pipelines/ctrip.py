# -*- coding: utf-8 -*-

import pymongo

from scrapy.conf import settings
from pymongo import MongoClient
from BusCrawl.spiders.ctrip import CTripSpider
from BusCrawl.spiders.cbd import CBDSpider
from BusCrawl.spiders.jsky import JskySpider


class MongoPipeline(object):
    def open_spider(self, spider):
        db_config = settings.get("MONGODB_CONFIG")
        self.client = MongoClient(db_config["url"])
        self.db = self.client[db_config["db"]]

        line_pks = [
            ("line_id", pymongo.ASCENDING),
            ("drv_date", pymongo.ASCENDING),
            ("drv_datetime", pymongo.ASCENDING),
        ]
        if isinstance(spider, CTripSpider):
            self.collection = self.db.ctrip_line
        elif isinstance(spider, CBDSpider):
            self.collection = self.db.cbd_line
        elif isinstance(spider, JskySpider):
            self.collection = self.db.jsky_line
        self.collection.create_index(line_pks, unique=True)

    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):
        pk = {
            "line_id": item["line_id"],
        }
        self.collection.replace_one(pk, dict(item), upsert=True)
