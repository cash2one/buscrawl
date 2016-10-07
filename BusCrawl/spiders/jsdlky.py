#!/usr/bin/env python
# encoding: utf-8
import scrapy
import json
import urllib
import datetime
import requests
import re

from datetime import datetime as dte
from BusCrawl.item import LineItem
from base import SpiderBase

START_STA_LIST = [
    {"query_code": "njkynz","stname":'南京客运南站'},
    {"query_code": 'njdz',"stname":'南京东站'},
    {"query_code": 'njbz',"stname":'南京北站'},
    {"query_code": 'jnkyz',"stname":'江宁客运站'},
    {"query_code": 'gcz',"stname":'高淳站'},
    {"query_code": 'lsz',"stname":'溧水站'},
    {"query_code": 'njgtz',"stname":'南京葛塘站'},
    {"query_code": 'njqckyz',"stname":'南京汽车客运站(小红山站)'}
]


class JsdlkySpider(SpiderBase):
    name = "jsdlky"
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipeline.MongoPipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
            'BusCrawl.middleware.MobileRandomUserAgentMiddleware': 400,
            # 'BusCrawl.middleware.ZjgsmHeaderMiddleware': 410,
            'BusCrawl.middleware.ProxyMiddleware': 410,
        },
        "DOWNLOAD_DELAY": 0.1,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
    }

    def get_dest_list_from_web(self, province, city, station=""):
        r = requests.get("http://www.jslw.gov.cn/index.do", headers={"Content-Type": "Chrome"})
        lst = []
        for s in re.findall(r"XX.module.address.source.fltDomestic =\"(\S+)\"", r.content)[0].split("@"):
            if not s:
                continue
            code, name, id = s.split("|")
            lst.append({"code": code, "name": unicode(name), "dest_id": id})
        return lst

    def get_dest_list(self, province, city, station=""):
        lst = super(JsdlkySpider, self).get_dest_list(province, city, station)
        lst2 = self.get_dest_list_from_web(province, city, station)
        tmp = {d["name"]:1 for d in lst2}

        new_lst = []
        for d in lst:
            if d["name"] in tmp:
                new_lst.append(d)
            else:
                print "ignore", d["name"]
        return new_lst

    def start_requests(self):
        # line_url = "http://58.213.132.27:8082/nj_weixinService/2.0/queryBus"
        line_url = "http://58.213.132.28/weixin/proxy/queryBus"
        today = datetime.date.today()
        trans = {"南京汽车客运站(小红山站)": "南京汽车客运站"}
        for sta_info in START_STA_LIST:
            start = {
                "city_name": "南京",
                "city_code": "nj",
                "sta_name": trans.get(sta_info["stname"], sta_info["stname"]),
                "sta_code": sta_info["query_code"],
            }
            for s in self.get_dest_list("江苏", start["city_name"], start["sta_name"]):
                name, code = s["name"], s["code"]
                end = {"city_name": name, "city_code": code}
                self.logger.info("start %s ==> %s" % (start["sta_name"], end["city_name"]))
                for i in range(self.start_day(), 8):
                    sdate = (today + datetime.timedelta(days=i)).strftime("%Y%m%d")
                    if self.has_done(start["sta_name"], end["city_name"], sdate):
                        continue
                    # params = {
                    #     "drive_date": sdate,
                    #     "rst_name": start["sta_name"],
                    #     "dst_name": end["city_name"],
                    #     "v_source": "a",
                    #     "v_version": "v2.2",
                    #     "v_reg_id": ""
                    # }
                    # req_data = {
                    #     "param_key": json.dumps(params),
                    #     "secret_key": md5("&".join(map(lambda a:"%s=%s" % (a[0], a[1]), sorted(params.items(), key=lambda i: i[0])))),
                    # }
                    req_data = {
                        "ewx": "6bjHP03wFIudTp+CXaQoQGwT2PvT3J0CDFbE4FwZ02KMMNcwsVKN6Ab0vbAMwsN0ochYbOMtaa+s/zbq84qvm6HPxOtoklekf6rww16xwzk=",
                        "drive_date": sdate,
                        "rst_name": start["sta_name"],
                        "dst_name": end["city_name"],
                    }
                    yield scrapy.Request("%s?%s" % (line_url, urllib.urlencode(req_data)),
                                         callback=self.parse_line,
                                         meta={"start": start, "end": end, "sdate": sdate})

    def parse_line(self, response):
        "解析班车"
        start = response.meta["start"]
        end= response.meta["end"]
        sdate = response.meta["sdate"]
        res = json.loads(response.body)
        if res["rtn_code"] != "00":
            self.logger.error("parse_line: Unexpected return, %s", res)
            return
        shift_list = res["data"] or []
        self.mark_done(start["sta_name"], end["city_name"], sdate)

        for d in shift_list:
            drv_datetime = dte.strptime("%s %s" % (d["drive_date"], d["plan_time"]), "%Y%m%d %H%M")
            s_sta_name = d["rst_name"]
            if u"��" in d["dst_name"]:
                continue
            if u"��" in s_sta_name:  # 有乱码
                s_sta_name = start["sta_name"]
            attrs = dict(
                s_province = "江苏",
                s_city_id = "",
                s_city_name = start["city_name"],
                s_sta_name = d["rst_name"],
                s_city_code= start["city_code"],
                s_sta_id= d["rstcode"],
                d_city_name = end["city_name"],
                d_city_id="",
                d_city_code=end["city_code"],
                d_sta_id=d["dstcode"],
                d_sta_name = d["dst_name"],
                drv_date = drv_datetime.strftime("%Y-%m-%d"),
                drv_time = drv_datetime.strftime("%H:%M"),
                drv_datetime = drv_datetime,
                distance = unicode(d["mileage"]),
                vehicle_type = d["m_name"],
                seat_type = "",
                bus_num = d["bus_code"],
                full_price = float(d["full_price"]),
                half_price = float(d["half_price"]),
                fee = 0,
                crawl_datetime = dte.now(),
                extra_info = {"startstation": d["sst_name"], "terminalstation": d["tst_name"], "startstationcode": d["sstcode"]},
                left_tickets = int(d["available_tickets"]),
                crawl_source = "jsdlky",
                shift_id="",
            )
            yield LineItem(**attrs)
