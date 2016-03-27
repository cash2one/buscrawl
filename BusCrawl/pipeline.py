# -*- coding: utf-8 -*-

from scrapy.conf import settings
from pymongo import MongoClient
from utils.tool import md5
from datetime import datetime as dte


class MongoPipeline(object):
    def open_spider(self, spider):
        db_config = settings.get("MONGODB_CONFIG")
        self.client = MongoClient(db_config["url"])
        db = self.client[db_config["db"]]
        self.collection = db.line

    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):
        err = item.valid()
        if err:
            spider.logger.error(err)
            return
        if item["full_price"] < 5:
            continue

        data = dict(item)
        now = dte.now()
        if data["province"] in ["江苏", "重庆"]:        # 后续会统一用这种方式
            data["line_id"]= md5("%(s_city_name)s-%(d_city_name)s-%(drv_datetime)s-%(s_sta_name)s-%(d_sta_name)s-%(crawl_source)s" % data)
        else:
            data["line_id"]= md5("%(s_city_name)s-%(d_city_name)s-%(drv_datetime)s-%(bus_num)s-%(crawl_source)s" % data)
        data["update_datetime"] = now
        data["refresh_datetime"] = now
        pk = {
            "line_id": data["line_id"],
        }
        self.collection.replace_one(pk, data, upsert=True)
