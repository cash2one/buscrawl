#!/usr/bin/env python
# encoding: utf-8

import scrapy
import datetime
import urllib
import requests
import re

from datetime import datetime as dte
from bs4 import BeautifulSoup as bs
from BusCrawl.item import LineItem
from BusCrawl.utils.tool import get_pinyin_first_litter
from base import SpiderBase

START_STATIONS = {
    u'济南长途汽车总站': 1,
    u'济南长途汽车总站南区': 2,
    u'济南长途汽车东站': 3,
    u'章丘长途汽车总站': 4,
}

class Glcx(SpiderBase):
    name = "glcx"
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipeline.MongoPipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
            'BusCrawl.middleware.BrowserRandomUserAgentMiddleware': 400,
            'BusCrawl.middleware.ProxyMiddleware': 410,
            'BusCrawl.middleware.GlcxHeaderMiddleware': 410,
        },
        "DOWNLOAD_DELAY": 0.1,
        # "RANDOMIZE_DOWNLOAD_DELAY": True,
    }


    def get_dest_list_from_web(self, province, city, station=""):
        r = requests.get("http://www.0000369.cn/buytks!list.action", headers={"User-Agent": "Chrome"})
        dest_list = []
        for t in re.findall(r"aff%s\[(\w+)\]= new Array\('(\W+)','(\w+)','(\w+)'\)" % START_STATIONS[station], r.content):
            idx, name, code, id = t
            name = unicode(name)
            dest_list.append({"name": name, "code": code, "dest_id": id})
        return dest_list

    def get_dest_list(self, province, city, station=""):
        dest_list = super(Glcx, self).get_dest_list(province, city, station)
        dest_list_web = self.get_dest_list_from_web(province, city, station)
        dest_list_web = {d["name"]: d["dest_id"] for d in dest_list_web}
        new_dest_list = []
        for d in dest_list:
            if d["name"] not in dest_list_web:
                continue
            d.update(dest_id=dest_list_web[d["name"]])
            new_dest_list.append(d)
        return new_dest_list


    def start_requests(self):
        today = datetime.date.today()
        line_url = 'http://www.0000369.cn/buytks!searchtks.action'
        for s_name, s_id in START_STATIONS.items():
            start = {"city_name": "济南", "city_code": "jn", "sta_name": s_name, "sta_id": s_id}
            for d in self.get_dest_list("山东", "济南", s_name):
                for y in xrange(self.start_day(), 8):
                    sdate = str(today + datetime.timedelta(days=y))
                    end = d
                    data = {
                        'stationId': start["sta_id"],
                        'portId': end["dest_id"],
                        'startTime': sdate,
                    }
                    if self.has_done(start["sta_name"], end["name"], sdate):
                        continue
                    yield scrapy.Request(url=line_url, callback=self.parse_line, method='POST', body=urllib.urlencode(data),meta={"start": start, "end": end, "sdate": sdate})

    def parse_line(self, response):
        start = response.meta['start']
        end = response.meta['end']
        sdate = response.meta['sdate'].decode('utf-8')
        self.mark_done(start["sta_name"], end["name"], sdate)
        self.logger.info("finish %s=>%s, %s", start["sta_name"], end["name"], sdate)

        soup = bs(response.body, 'lxml')
        for tr_o in soup.select("table #selbuy"):
            td_lst = tr_o.find_all('td')
            if len(td_lst) < 2:
                continue
            index_tr = lambda idx: td_lst[idx].text.strip().decode("utf-8")

            drv_date, drv_time = sdate, index_tr(1)
            if u"流水" in drv_time:
                continue
            attrs = dict(
                s_province='山东',
                s_city_id="",
                s_city_name=start["city_name"],
                s_sta_name=start["sta_name"],
                s_city_code=start["city_code"],
                s_sta_id=start["sta_id"],
                d_city_name=end["name"],
                d_city_id=end["dest_id"],
                d_city_code=end["code"],
                d_sta_id=end["dest_id"],
                d_sta_name=end["name"],
                drv_date=drv_date,
                drv_time=drv_time,
                drv_datetime=dte.strptime("%s %s" % (drv_date, drv_time), "%Y-%m-%d %H:%M"),
                distance='',
                vehicle_type=index_tr(4),
                seat_type="",
                bus_num=index_tr(0),
                full_price=float(index_tr(6)),
                half_price=float(index_tr(6)) / 2,
                fee=0.0,
                crawl_datetime=dte.now(),
                extra_info={"startNo": index_tr(11)},
                left_tickets=int(index_tr(10)),
                crawl_source="glcx",
                shift_id="",
            )
            if attrs["left_tickets"]:
                yield LineItem(**attrs)
