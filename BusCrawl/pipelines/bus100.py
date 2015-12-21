# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

import pymongo

from pymongo import MongoClient
from BusCrawl.items.bus100 import LineItem, StartCityItem, TargetCityItem


class MongoBus100Pipeline(object):
    def open_spider(self, spider):
        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client["crawl12308"]

        start_pks = [("start_city_id", pymongo.ASCENDING)]
        self.db.start_city_bus100.create_index(start_pks, unique=True)

        end_pks = [
            ("target_name", pymongo.ASCENDING),
            ("starting_id", pymongo.ASCENDING),
        ]
        self.db.target_city_bus100.create_index(end_pks, unique=True)

        line_pks = [
            ("line_id", pymongo.ASCENDING)
        ]
        self.db.line_bus100.create_index(line_pks, unique=True)

    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):
        if not spider.name == "bus100":
            return
        if isinstance(item, StartCityItem):
            pk = {"start_city_name": item["start_city_name"], "start_city_id": item["start_city_id"]}
            self.db.start_city_bus100.replace_one(pk, dict(item), upsert=True)
        elif isinstance(item, TargetCityItem):
            pk = {
                "starting_id": item["starting_id"],
                "target_name": item["target_name"]
            }
            self.db.target_city_bus100.replace_one(pk, dict(item), upsert=True)
        if isinstance(item, LineItem):
            query = {
                    "line_id": item["line_id"],
                   }
            self.db.line_bus100.update(query, {"$set": dict(item)}, upsert=True)
        return item
