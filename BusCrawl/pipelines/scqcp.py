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

        start_pks = [("city_id", pymongo.ASCENDING)]
        self.db.start_city.create_index(start_pks, unique=True)

        end_pks = [
            ("stop_name", pymongo.ASCENDING),
            ("starting_city_id", pymongo.ASCENDING),
        ]
        self.db.target_city.create_index(end_pks, unique=True)

        line_pks = [
            ("carry_sta_id", pymongo.ASCENDING),
            ("sign_id", pymongo.ASCENDING),
            ("stop_name", pymongo.ASCENDING),
            ("drv_date_time", pymongo.ASCENDING),
        ]
        self.db.line.create_index(line_pks, unique=True)

    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):
        if isinstance(item, StartCityItem):
            pk = {"city_id": item["city_id"]}
            self.db.start_city.replace_one(pk, dict(item), upsert=True)
        elif isinstance(item, TargetCityItem):
            pk = {
                "starting_city_id": item["starting_city_id"],
                "stop_name": item["stop_name"]
            }
            self.db.target_city.replace_one(pk, dict(item), upsert=True)
        elif isinstance(item, LineItem):
            pk = {
                "carry_sta_id": item["carry_sta_id"],
                "sign_id": item["sign_id"],
                "stop_name": item["stop_name"],
                "drv_date_time": item["drv_date_time"],
            }
            self.db.line.replace_one(pk, dict(item), upsert=True)
        return item
