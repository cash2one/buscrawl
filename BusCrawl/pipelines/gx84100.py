# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

import pymongo

from pymongo import MongoClient
from BusCrawl.items.gx84100 import LineItem, StartCityItem, TargetCityItem


class MongoGx84100Pipeline(object):
    def open_spider(self, spider):
        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client["crawl12308"]

    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):
        if not spider.name == "crawl12308":
            return
        if isinstance(item, StartCityItem):
            pk = {"city_name": item["city_name"]}
            self.db.start_city_gx84100.replace_one(pk, dict(item), upsert=True)
        elif isinstance(item, TargetCityItem):
            pk = {
                "starting_id": item["starting_id"],
                "target_name": item["target_name"]
            }
            self.db.target_city_gx84100.replace_one(pk, dict(item), upsert=True)
        if isinstance(item, LineItem):
            query={
                   'start_city_name': item["start_city_name"],
                   "start_city_id": item["start_city_id"],
                   "target_city_name": item["target_city_name"],
                   "departure_time": item["departure_time"],
                   }
            self.db.line_gx84100.update(query,{"$set":dict(item)},upsert=True)
        return item
