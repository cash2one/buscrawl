# -*- coding: utf-8 -*-
import scrapy
import json
import datetime

from datetime import datetime as dte
from BusCrawl.item import LineItem
from base import SpiderBase
from BusCrawl.utils.tool import md5


class ScqcpSpider(SpiderBase):
    name = "scqcp"
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipeline.MongoPipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
            'BusCrawl.middleware.MobileRandomUserAgentMiddleware': 400,
            'BusCrawl.middleware.ProxyMiddleware': 410,
            'BusCrawl.middleware.ScqcpHeaderMiddleware': 410,
        },
        "DOWNLOAD_DELAY": 0.2,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
    }
    md5_key = "sdkjfgweysdgfvgvehbfhsdfgvbwjehfsdf"

    def post_data_templ(self, api, content, sign):
        tmpl = {
            "head": {
                    "sign": sign,
                    "server": api,
                    "token": "04b8cef68ef4f2d785150eb671999834",
                    "ip": "192.168.3.116",
                    "version": "1.5.1",
                    "signType": "MD5"},
            "body": content
        }
        return tmpl

    def get_md5_sign(self, params):
        ks = params.keys()
        ks.sort()
        rlt = ''
        for k in ks:
            if params[k] == None or len(params[k]) == 0:
                continue
            rlt = rlt+"&%s=%s" % (k, params[k])
        return md5(rlt[1:]).upper()

    def start_requests(self):
        start_url = "http://inner.cdqcp.com/ticket"
        content = {}
        api = 'getAllStartCity'
        sign = "754790439CDE44E39D29BA3508BC0CF3"
        fd = self.post_data_templ(api, content, sign)
        yield scrapy.Request(start_url,
                             method="POST",
                             body=json.dumps(fd),
                             callback=self.parse_start_city)

    def parse_start_city(self, response):
        "解析出发城市"
        res = json.loads(response.body)
        url = "http://inner.cdqcp.com/ticket"
        for province in res['body']["start_city"]:
            if not self.is_need_crawl(province=province["province_name"]):
                continue
            for d in province['city']:
                if not self.is_need_crawl(city=d["city_name"]):
                    continue
                if not d["is_pre_sell"]:
                    self.logger.error("%s 没开放售票", d["city_name"])
                    continue
                content = {"cityId": unicode(d["city_id"]), "cityName": unicode(d["city_name"])}
                api = "getTargetCity"
                params = {}
                params.update(content)
                params.update({"key": self.md5_key})
                sign = self.get_md5_sign(params)
                fd = self.post_data_templ(api, content, sign)
                start = {
                    "province": province["province_name"].strip().rstrip(u"省"),
                    "city_id": str(d["city_id"]),
                    "city_name": d["city_name"],
                    "city_code": d["short_name"],
                }
                yield scrapy.Request(url,
                                     method="POST",
                                     body=json.dumps(fd),
                                     callback=self.parse_target_city,
                                     meta={"start": start})

    def parse_target_city(self, response):
        "解析目的地城市"
        res = json.loads(response.body)

        url = "http://inner.cdqcp.com/ticket"
        start = response.meta["start"]
        for d in res['body']["target_city"]:
            start.update({
                "sta_id": d["carry_sta_id"],
                "sta_name": d["carry_sta_name"],
            })
            end = {
                "city_name": d["stop_name"],
                "city_code": d["short_name"],
                "sta_name": d["stop_name"],
                "sta_id": "",
            }

            # 预售期5天, 节假日预售期10天
            today = datetime.date.today()
            for i in range(1, 11):
                sdate = str(today+datetime.timedelta(days=i))
                if self.has_done(start["city_name"], end["city_name"], sdate):
                    self.logger.info("ignore %s ==> %s %s" % (start["city_name"], end["city_name"], sdate))
                    continue
                content = {"ridingDate": sdate,
                           "stopName": d["stop_name"],
                           "cityId": start["city_id"],
                           "cityName": start["city_name"]
                           }
                api = "queryByCity"
                params = {}
                params.update(content)
                params.update({"key": self.md5_key})
                sign = self.get_md5_sign(params)
                fd = self.post_data_templ(api, content, sign)
                yield scrapy.Request(url,
                                     method="POST",
                                     body=json.dumps(fd),
                                     callback=self.parse_line,
                                     meta={"start": start, "end": end, "sdate": sdate})

    def parse_line(self, response):
        "解析班车"
        res = json.loads(response.body)
        start = response.meta["start"]
        end = response.meta["end"]
        sdate = response.meta["sdate"]
        self.mark_done(start["city_name"], end["city_name"], sdate)
        for d in res['body']["ticketLines"]:
            drv_datetime = dte.strptime(d["drvDateTime"], "%Y-%m-%d %H:%M")
            drv_date, drv_time = d["drvDateTime"].split(" ")
            if int(d["amount"]) == 0:
                continue
            attrs = dict(
                s_province=start["province"],
                s_city_name=start["city_name"],
                s_city_id=start["city_id"],
                s_city_code=start["city_code"],
                s_sta_name=d["carryStaName"],
                s_sta_id=d["carryStaId"],
                d_city_name=d["stopName"],
                d_city_id="",
                d_city_code=end["city_code"],
                d_sta_name=d["stopName"],
                d_sta_id="",
                drv_date=drv_date,
                drv_time=drv_time,
                drv_datetime=drv_datetime,
                distance=d["mile"],
                vehicle_type=d["busTypeName"],
                seat_type="",
                bus_num=d["schId"],
                full_price=float(d["fullPrice"]),
                half_price=float(d["halfPrice"]),
                fee = float(d["servicePrice"]),
                crawl_datetime = dte.now(),
                extra_info = {"sign_id": d["signId"]},
                left_tickets = int(d["amount"]),
                crawl_source = "scqcp",
                shift_id="",
            )
            yield LineItem(**attrs)
