#!/usr/bin/env python
# encoding: utf-8

import scrapy
import json
import datetime
import re
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

from datetime import datetime as dte
from BusCrawl.item import LineItem
from base import SpiderBase

from BusCrawl.utils.tool import get_pinyin_first_litter


class ShkyzzSpider(SpiderBase):
    name = "shkyzz"
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipeline.MongoPipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
            'BusCrawl.middleware.BrowserRandomUserAgentMiddleware': 400,
            'BusCrawl.middleware.ProxyMiddleware': 410,
            'BusCrawl.middleware.ShkyzzHeaderMiddleware': 410,
        },
        "DOWNLOAD_DELAY": 0.2,
#         "RANDOMIZE_DOWNLOAD_DELAY": True,
    }

    def start_requests(self):
        url = "http://www.zxjt.sh.cn/ajax/flightJsonAction!searchCitys?region=arriveRegion&city=%E4%B8%8A%E6%B5%B7"
        return [scrapy.Request(url, callback=self.parse_target_city)]
 
    def parse_target_city(self, response):
        "解析目的地城市"
        res = json.loads(response.body)
        dest_list = set()
        city_name = '上海'
        for k, v in res["cityMap"].items():
            dest_list = dest_list.union(set(v))
        print dest_list
        print len(dest_list)
        url = "http://www.zxjt.sh.cn/ajax/flightJsonAction!search"
        for d in dest_list:
            today = datetime.date.today()
            for i in range(0, 3):
                sdate = str(today+datetime.timedelta(days=i))
#                 if self.has_done(city_name, d, sdate):
#                     self.logger.info("ignore %s ==> %s %s" % (city_name, d, sdate))
#                     continue
                fd = {
                  "searchForm.fromRegionName": city_name,
                  "searchForm.arriveRegionName": d,
                  "searchForm.flightDate": sdate,
                  "__multiselect_searchForm.stationIdArr": '',
                  "searchForm.startDate": '',
                  "searchForm.selFlightCountFlag": "true",
                }
                yield scrapy.FormRequest(url,
                                         formdata=fd,
                                         callback=self.parse_line,
                                         meta={"start": city_name, "end": d, "sdate": sdate})

    def parse_line(self, response):
        "解析班车"
        start = response.meta["start"]
        end = response.meta["end"]
        sdate = response.meta["sdate"]
#         self.logger.info("finish %s ==> %s" % (start, end))
#         self.mark_done(start, end, sdate)
        res = json.loads(response.body)
        sch_list = res['flightList']
        {
        u'arriveStationName': None,
        u'arriveRegionName': u'泰安',
        u'arriveRegionId': u'1000001449',
        u'fromRegionName': u'上海',
        u'flightCount': 30,
        u'indexNo': None,
        u'flightIndex': 0,
        u'flightOnlineId': u'1609070060211000016',
        u'onlineDetail': None,
        u'stationAddress': u'中兴路1666号',
        u'stationPrintName': u'客运总站',
        u'endRegionId': u'1000000353',
        u'vehicleId': None,
        u'companyId': u'1000001650',
        u'flightActualDetailId': u'1609070060212',
        u'flightDate': u'2016-09-07',
        u'endProvinceId': u'37',
        u'arriveProvinceName': u'山东',
        u'vehicleTypeGrade': u'41002',
        u'onlineCount': None,
        u'mileage': None,
        u'flightStatus': u'Y',
        u'companyName': u'上海白玉兰高速客运有限公司',
        u'price': 246,
        u'onlineStatus': u'Y',
        u'endProvinceName': u'山东',
        u'fromRegionId': None,
        u'flightActualId': u'160907006021',
        u'stationId': u'1000016',
        u'saledCount': 0,
        u'stationName': u'上海长途客运总站',
        u'endRegionName': u'济南',
        u'fromProvinceId': None,
        u'flightNo': u'006021',
        u'fromSystem': u'上海公路客运',
        u'arriveProvinceId': u'37',
        u'vehicleTypeBrand': u'40002',
        u'seatType': None,
        u'lastCount': 24,
        u'halfPrice': 123,
        u'fromProvinceName': None,
        u'flightOnlineDetailId': u'16090700602121000016',
        u'vehicleNo': None,
        u'flightTime': u'20: 50'
    }

        for d in sch_list:
            attrs = dict(
                s_province='上海',
                s_city_name=start,
                s_city_id = '',
                s_city_code= get_pinyin_first_litter(unicode(start)),
                s_sta_name= d['stationName'],
                s_sta_id = d['stationId'],
                d_city_name = d['arriveRegionName'],
                d_city_code= get_pinyin_first_litter(d['arriveRegionName']),
                d_city_id = d['arriveRegionId'],
                d_sta_name = d['arriveRegionName'],
                d_sta_id = '',
                drv_date = sdate,
                drv_time = d['flightTime'],
                drv_datetime = dte.strptime("%s %s" % (sdate, d['flightTime']), "%Y-%m-%d %H:%M"),
                distance = '0',
                vehicle_type = "",
                seat_type = '',
                bus_num = d['flightNo'],  
                full_price = float(d['price']),
                half_price = float(d['halfPrice']),
                fee = 0,
                crawl_datetime = dte.now(),
                extra_info = {"raw_info": d},
                left_tickets = int(d['lastCount']),
                crawl_source = "shkyzz",
                shift_id='',
            )
            yield LineItem(**attrs)


