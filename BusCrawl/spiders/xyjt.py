#!/usr/bin/env python
# encoding: utf-8

import scrapy
import datetime
import urllib
from bs4 import BeautifulSoup as bs
from datetime import datetime as dte
from BusCrawl.item import LineItem
from base import SpiderBase


class Xyjt(SpiderBase):
    name = "xyjt"
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipeline.MongoPipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
            'BusCrawl.middleware.BrowserRandomUserAgentMiddleware': 400,
            'BusCrawl.middleware.XyjtHeaderMiddleware': 400,
            # 'BusCrawl.middleware.ProxyMiddleware': 410,
        },
        "DOWNLOAD_DELAY": 0.25,
        # "RANDOMIZE_DOWNLOAD_DELAY": True,
    }

    # 用于测试
    # def get_dest_list(self, province, city, station=""):
    #     return [{"code": "sz", "name": "苏州", "dest_id": ""}]

    def start_requests(self):
        yield scrapy.Request("http://order.xuyunjt.com/wsdgbccx.aspx", callback=self.parse_start)

    def parse_start(self, response):
        soup = bs(response.body, "lxml")
        vs = soup.select_one("#__VIEWSTATE").get("value")
        today = dte.today()
        line_url = "http://order.xuyunjt.com/wsdgbccx.aspx"
        for obj in soup.find("select", attrs={"name": "ctl00$ContentPlaceHolder1$ddlincounty"}).select("option"):
            sta_id, sta_name = obj.get('value'), obj.text.strip()
            if not sta_name or not sta_id:
                continue
            start = {
                "city_name": "徐州",
                "city_code": "xz",
                "city_id": "",
                "sta_name": sta_name,
                "sta_id": sta_id,
            }
            data = {
                'ctl00$ContentPlaceHolder1$ScriptManager1': 'ctl00$ContentPlaceHolder1$ScriptManager1|ctl00$ContentPlaceHolder1$BtnBccx',
                '__EVENTARGUMENT': '',
                '__LASTFOCUS': '',
                '__VIEWSTATE': vs,
                'ctl00$ContentPlaceHolder1$ddlincounty': start["sta_id"],
                'ctl00$ContentPlaceHolder1$ddlsaledate': today.strftime("%Y%m%d"),
                'ctl00$ContentPlaceHolder1$txtstop': "南京",
                'radio': "南京",
            }
            yield scrapy.Request(url=line_url, callback=self.parse_viewstate, method='POST',body=urllib.urlencode(data), meta={"start": start})

    def parse_viewstate(self, response):
        soup = bs(response.body, "lxml")
        vs = soup.select_one("#__VIEWSTATE").get("value")
        start = response.meta['start']
        today = dte.today()
        line_url = "http://order.xuyunjt.com/wsdgbccx.aspx"
        dest_list = self.get_dest_list("江苏", "徐州", station=unicode(start["sta_name"]))
        if not dest_list:
            return
        for d in dest_list:
            for i in xrange(self.start_day(), 8):
                dt = (today + datetime.timedelta(days=i)).today()
                sdate = dt.strftime("%Y%m%d")
                if self.has_done(start["sta_name"], d["name"], sdate):
                    continue
                data = {
                    'ctl00$ContentPlaceHolder1$ScriptManager1': 'ctl00$ContentPlaceHolder1$ScriptManager1|ctl00$ContentPlaceHolder1$BtnBccx',
                    'ctl00$ContentPlaceHolder1$BtnBccx': '班次查询',
                    '__EVENTARGUMENT': '',
                    '__LASTFOCUS': '',
                    '__VIEWSTATE': vs,
                    'ctl00$ContentPlaceHolder1$ddlincounty': start["sta_id"],
                    'ctl00$ContentPlaceHolder1$ddlsaledate': sdate,
                    'ctl00$ContentPlaceHolder1$txtstop': d["name"],
                    'radio': "",
                }
                end = d
                yield scrapy.Request(url=line_url, callback=self.parse_line, method='POST',body=urllib.urlencode(data), meta={"start": start, "end": end, "sdate": sdate})

    def parse_line(self, response):
        start = response.meta['start']
        end = response.meta['end']
        sdate = response.meta['sdate']
        self.mark_done(start["sta_name"], end["name"], sdate)
        soup = bs(response.body, 'lxml')
        for tr_o in soup.select("#ctl00_ContentPlaceHolder1_GVBccx tr")[1:]:
            if tr_o.get("class") and "GridViewHeaderStyle" in tr_o.get("class"):
                continue
            td_lst = tr_o.select("td")
            index_tr = lambda idx: td_lst[idx].text.strip()
            drv_date, drv_time = index_tr(0), index_tr(5)
            if u"流水" in drv_time:
                continue
            attrs = dict(
                s_province='江苏',
                s_city_id=start["city_id"],
                s_city_name=start["city_name"],
                s_sta_name=index_tr(1),
                s_city_code=start["city_code"],
                s_sta_id=start["sta_id"],
                d_city_name=end["name"],
                d_city_id="",
                d_city_code=end["code"],
                d_sta_id="",
                d_sta_name=index_tr(3),
                drv_date=drv_date,
                drv_time=drv_time,
                drv_datetime=dte.strptime("%s %s" % (drv_date, drv_time), "%Y-%m-%d %H:%M"),
                distance=unicode(index_tr(11)),
                vehicle_type=unicode(index_tr(10)),
                seat_type="",
                bus_num=index_tr(2),
                full_price=float(index_tr(6)),
                half_price=float(index_tr(7)),
                fee=0,
                crawl_datetime=dte.now(),
                extra_info={"lock_url": td_lst[12].find("a").get("href")},
                left_tickets=int(index_tr(8)),
                crawl_source="xyjt",
                shift_id="",
            )
            yield LineItem(**attrs)
