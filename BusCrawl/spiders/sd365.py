# !/usr/bin/env python
# encoding: utf-8

import scrapy
import json
import datetime
import urllib
import requests

from bs4 import BeautifulSoup as bs
from datetime import datetime as dte
from BusCrawl.item import LineItem
from base import SpiderBase
from BusCrawl.utils.tool import get_redis

PROVINCE_TO_CITY = {
    "山东": ["烟台市","蓬莱市","海阳市","栖霞市","招远市","莱州市","莱阳市","龙口市","济南市","滕州市","淄博市","济宁市","滨州市","东营市","聊城市","德州市","潍坊市","三门峡","莱芜市","枣庄市","威海市","榆林","临沂市","文登","荣成","乳山","石岛","寿光","泰安","新泰市","肥城市","菏泽市"],
    "天津": ["天津市",]
}

CITY_TO_PROVINCE = {}
for p, lst in PROVINCE_TO_CITY.items():
    for c in lst:
        CITY_TO_PROVINCE[unicode(c)] = p


class Sd365(SpiderBase):
    name = "sd365"
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipeline.MongoPipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
            'BusCrawl.middleware.BrowserRandomUserAgentMiddleware': 400,
            'BusCrawl.middleware.Sd365ProxyMiddleware': 410,
        },
        "DOWNLOAD_DELAY": 0.1,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
    }

    @classmethod
    def proxy_get(cls, url, **kwargs):
        rds = get_redis()
        for i in range(10):
            ipstr = rds.srandmember("proxy:sd365")
            if ipstr:
                kwargs["proxies"] = {"http": "http://%s" % ipstr}
            r = requests.get(url, **kwargs)
            if r.status_code == 200:
                return r

    @classmethod
    def get_all_start_cities(cls):
        if not hasattr(cls, "_name_to_info"):
            url = 'http://www.36565.cn/js/data/buscityjs.js'
            r = cls.proxy_get(url, headers={"User-Agent": "Chrome/51.0.2704.106"})
            name_to_info = {}
            # pls|蓬莱市|370600|penglaishi|pls|370684
            for s in r.json().values()[0].split('@'):
                if not s:
                    continue
                code, name, parent_id, pinyin, code, my_id = s.split("|")
                name_to_info[name] = {"name": name, "code": code, "parent_id": parent_id, "id": my_id, "province": CITY_TO_PROVINCE[name]}
            cls._name_to_info = name_to_info
        return cls._name_to_info

    def get_dest_list_from_web(self, province, city, station=""):
        start_info = self.get_all_start_cities()[city]
        url = "http://www.365tkt.com/js/data/cityport_%s.js" % start_info["parent_id"]
        r = self.proxy_get(url, headers={"User-Agent": "Chrome/51.0.2704.106"})

        lst = []
        for line in r.content.split(";"):
            if not line:
                continue
            tmp_lst = eval(line.split("=")[1].strip())
            # tmp_lst eg: ['123401', '诸城', 'ZC', 'ZHUCHENG']
            if not tmp_lst:
                continue
            dest_id, name, code, py = tmp_lst
            lst.append({"code": code, "name": name, "dest_id": dest_id})
        return lst

    def start_requests(self):
        today = datetime.date.today()
        for name, s_info in self.get_all_start_cities().items():
            start = s_info
            if not self.is_need_crawl(start["province"], start["name"]):
                continue
            for d_info in self.get_dest_list(start["province"], start["name"]):
                end = d_info
                url = 'http://www.36565.cn/?c=tkt3&a=search&fromid=&from={0}&toid=&to={1}&date={2}&time=0#'.format(start["name"], end["name"], str(today + datetime.timedelta(days=1)))
                yield scrapy.Request(url=url, callback=self.parse_line_pre,meta={'start': start, 'end': end})

    def parse_line_pre(self, response):
        start = response.meta['start']
        end = response.meta['end']
        days = 8
        today = datetime.date.today()
        code = response.body.split('code:')[-1].split()[0].split('"')[1]
        soup = bs(response.body, 'lxml')
        info = soup.find_all('input', attrs={'class': 'filertctrl', 'name': 'siids'})
        sids = ','.join([x["value"] for x in info])
        for y in xrange(self.start_day(), days):
            sdate = str(today + datetime.timedelta(days=y))
            if self.has_done(start, end, sdate):
                continue
            data = {
                'a': 'getlinebysearch',
                'c': 'tkt3',
                'toid': '',
                'type': '0',
                'code': code,
                'date': sdate,
                'sids': sids,
                'to': end["name"],
            }
            last_url = 'http://www.36565.cn/?' + urllib.urlencode(data)
            yield scrapy.Request(url=last_url, callback=self.parse_line, meta={'start': start, 'end': end, 'sdate': sdate})

    def parse_line(self, response):
        if response.body.strip() == "[]":
            return
        res_lst = json.loads(response.body)
        start = response.meta['start']
        end = response.meta['end']
        sdate = response.meta['sdate']
        self.mark_done(start, end, sdate)
        self.logger.info("finish %s==>%s %s", start["name"], end["name"], sdate)
        for x in res_lst:
            drv_date = x['bpnDate']
            drv_time = x['bpnSendTime']
            s_sta_name = x['shifazhan']
            s_sta_id = x['siID']
            d_sta_name = x['prtName']
            left_tickets = x['bpnLeftNum']
            vehicle_type = x['btpName']
            extra = {
                'sid': x['siID'],
                'dpid': x['prtID'],
                'l': x['bliID'],
                't': x['bpnDate'],
            }
            bus_num = x['bliID']
            full_price = x['prcPrice']
            attrs = dict(
                s_province=start["province"],
                s_city_id=start["id"],
                s_city_name=start["name"],
                s_sta_name=s_sta_name,  # 不太确定
                s_city_code=start["code"],
                s_sta_id=s_sta_id,
                d_city_name=end["name"],
                d_city_id=end["dest_id"],
                d_city_code=end["code"],
                d_sta_id="",
                d_sta_name=d_sta_name,
                drv_date=drv_date,
                drv_time=drv_time,
                drv_datetime=dte.strptime("%s %s" % (drv_date, drv_time), "%Y-%m-%d %H:%M"),
                distance='',
                vehicle_type=vehicle_type,
                seat_type="",
                bus_num=bus_num,
                full_price=float(full_price),
                half_price=float(full_price) / 2,
                fee=0.0,
                crawl_datetime=dte.now(),
                extra_info=extra,
                left_tickets=int(left_tickets),
                crawl_source="sd365",
                shift_id="",
            )
            if int(left_tickets):
                yield LineItem(**attrs)
