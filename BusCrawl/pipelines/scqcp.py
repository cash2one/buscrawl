# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

import pymongo

from pymongo import MongoClient
from BusCrawl.items.scqcp import StartCityItem, TargetCityItem, LineItem


class MongoPipeline(object):
    def open_spider(self, spider):
        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client["scqcp"]
        self.db.start_city.create_index([("city_id", pymongo.ASCENDING)], unique=True)
        self.db.target_city.create_index([("stop_name", pymongo.ASCENDING), ("starting_city_id", pymongo.ASCENDING)], unique=True)
        self.db.line.create_index([("json_str_hash", pymongo.ASCENDING)], unique=True)

    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):
        if not spider.name == "scqcp":
            return
        if isinstance(item, StartCityItem):
            self.db.start_city.replace_one({"city_id": item["city_id"]}, dict(item), upsert=True)
        elif isinstance(item, TargetCityItem):
            self.db.target_city.replace_one(
                    {"starting_city_id": item["starting_city_id"], "stop_name": item["stop_name"]},
                     dict(item), upsert=True)
        elif isinstance(item, LineItem):
            self.db.line.replace_one({"json_str_hash": item["json_str_hash"]}, dict(item), upsert=True)
        return item
