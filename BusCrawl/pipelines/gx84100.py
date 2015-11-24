# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

import pymongo

from pymongo import MongoClient
from BusCrawl.items.gx84100 import  LineItem


class MongoGx84100Pipeline(object):
    def open_spider(self, spider):
        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client["gx84100"]

    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):
        if not spider.name == "gx84100":
            return
        if isinstance(item, LineItem):
            query={
                   'start_city_name':item["start_city_name"],
                   "start_city_id":item["start_city_id"],
                   "target_city_name":item["target_city_name"],
                   "departure_time":item["departure_time"],
                   }
            self.db.line.update(query,{"$set":dict(item)},upsert=True)
        return item
