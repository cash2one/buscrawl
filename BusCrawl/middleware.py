# -*- coding:utf-8 -*-
import random
from scrapy.contrib.downloadermiddleware.useragent import UserAgentMiddleware
from BusCrawl.utils.tool import get_redis


class ProxyMiddleware(object):
    "代理ip切换"

    def process_request(self, request, spider):
#         request.meta['proxy'] = "http://192.168.1.53:8888" 
        pass


class CqkyProxyMiddleware(object):
    "代理ip切换"

    def process_request(self, request, spider):
        rds = get_redis()
        ipstr = rds.srandmember("proxy:cqky")
        if ipstr:
            request.meta['proxy'] = "http://%s" % ipstr


class E8sProxyMiddleware(object):
    "代理ip切换"

    def process_request(self, request, spider):
        rds = get_redis()
        ipstr = rds.srandmember("proxy:e8s")
        if ipstr:
            request.meta['proxy'] = "http://%s" % ipstr


class CbdHeaderMiddleware(object):

    def process_request(self, request, spider):
        request.headers.setdefault("Content-Type", "application/json; charset=UTF-8")


class Lvtu100HeaderMiddleware(object):

    def process_request(self, request, spider):
        request.headers.setdefault("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8")


class ZjgsmHeaderMiddleware(object):

    def process_request(self, request, spider):
        request.headers.setdefault("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8")


class BabaHeaderMiddleware(object):

    def process_request(self, request, spider):
        request.headers.setdefault("Content-Type", "application/json; charset=UTF-8")
        request.headers.setdefault("Cookie", "vsid_=key7i7n3nzyj4glmxivlbdmgbjvbvwgjjla5fyn46a5mtackwp55e3kufluiziwlp3rdzbyr6c454")
        request.headers.setdefault("Cookie2", "$Version=1")


class TongChengHeaderMiddleware(object):

    def process_request(self, request, spider):
        request.headers.setdefault("Content-Type", "application/x-www-form-urlencoded")


class CqkyHeaderMiddleware(object):

    def process_request(self, request, spider):
        request.headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
        request.headers.setdefault("Origin", "http://www.96096kp.com/Default.aspx")
        request.headers.setdefault("Referer", "http://www.96096kp.com/Default.aspx")


class FangBianHeaderMiddleware(object):

    def process_request(self, request, spider):
        request.headers.setdefault("Content-Type", "application/x-www-form-urlencoded")


class JskyHeaderMiddleware(object):

    def process_request(self, request, spider):
        request.headers.setdefault("Content-Type", "application/json; charset=UTF-8")
        request.headers.setdefault("reqdata", "f3939b9644340ad093b70a09d2e3cc3c")


class CtripHeaderMiddleware(object):

    def process_request(self, request, spider):
        request.headers.setdefault("Content-Type", "application/json; charset=UTF-8")
        request.headers.setdefault("Authorization", "04b8cef68ef4f2d785150eb671999834")
        request.headers.setdefault("X-Requested-With", "ctrip.android.view")


class ScqcpHeaderMiddleware(object):

    def process_request(self, request, spider):
        request.headers.setdefault("Content-Type", "application/json; charset=UTF-8")
        request.headers.setdefault("Authorization", "04b8cef68ef4f2d785150eb671999834")


class GzqcpHeaderMiddleware(object):

    def process_request(self, request, spider):
        request.headers.setdefault("Content-Type", "application/x-www-form-urlencoded")


class KuaibaHeaderMiddleware(object):

    def process_request(self, request, spider):
        request.headers.setdefault("Content-Type", "application/x-www-form-urlencoded")


class BjkyHeaderMiddleware(object):

    def process_request(self, request, spider):
        request.headers.setdefault("Content-Type", "application/x-www-form-urlencoded")


class LnkyHeaderMiddleware(object):

    def process_request(self, request, spider):
        request.headers.setdefault("Content-Type", "application/x-www-form-urlencoded")


class HebkyHeaderMiddleware(object):

    def process_request(self, request, spider):
        request.headers.setdefault("Content-Type", "application/x-www-form-urlencoded")


class NmghyHeaderMiddleware(object):

    def process_request(self, request, spider):
        request.headers.setdefault("Content-Type", "application/x-www-form-urlencoded")


class Bus365HeaderMiddleware(object):

    def process_request(self, request, spider):
        request.headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
        request.headers.setdefault("accept", "application/json,")
        request.headers.setdefault("User-Agent", "Apache-HttpClient/UNAVAILABLE (java 1.4)")
        request.headers.setdefault("clienttype", "android")
        request.headers.setdefault("clienttoken", "")


class SzkyHeaderMiddleware(object):

    def process_request(self, request, spider):
        request.headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
        request.headers.setdefault("accept", "application/json")
        request.headers.setdefault("X-Requested-With", "XMLHttpRequest")


class DgkyHeaderMiddleware(object):

    def process_request(self, request, spider):
        request.headers.setdefault("Content-Type", "application/x-www-form-urlencoded")


class WmcxHeaderMiddleware(object):

    def process_request(self, request, spider):
        request.headers.setdefault("Content-Type", "application/json; charset=UTF-8")
        request.headers.setdefault("Cookie", "vsid_=key7i7n3nzyj4glmxivlbdmgbjvbvwgjjla5fyn46a5mtackwp55e3kufluiziwlp3rdzbyr6c454")
        request.headers.setdefault("Cookie2", "$Version=1")


class MobileRandomUserAgentMiddleware(UserAgentMiddleware):
    "移动端UserAgent"

    user_agent_list = [
        "Mozilla/5.0 (Linux; U; Android 4.0.3; ko-kr; LG-L160L Build/IML74K) AppleWebkit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30",
        "Mozilla/5.0 (Linux; U; Android 4.0.3; de-ch; HTC Sensation Build/IML74K) AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30",
        "Mozilla/5.0 (Linux; U; Android 2.3; en-us) AppleWebKit/999+ (KHTML, like Gecko) Safari/999.9",
        "Mozilla/5.0 (Linux; U; Android 2.3.5; zh-cn; HTC_IncredibleS_S710e Build/GRJ90) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1",
        "Mozilla/5.0 (Linux; U; Android 2.3.5; en-us; HTC Vision Build/GRI40) AppleWebKit/533.1 (KHTML, like Gecko) \
            Version/4.0 Mobile Safari/533.1",
        "Mozilla/5.0 (Linux; U; Android 2.3.4; fr-fr; HTC Desire Build/GRJ22) AppleWebKit/533.1 (KHTML, like Gecko) \
            Version/4.0 Mobile Safari/533.1",
        "Mozilla/5.0 (Linux; U; Android 2.3.4; en-us; T-Mobile myTouch 3G Slide Build/GRI40) AppleWebKit/533.1 (KHTML, \
            like Gecko) Version/4.0 Mobile Safari/533.1",
        "Mozilla/5.0 (Linux; U; Android 2.3.3; zh-tw; HTC_Pyramid Build/GRI40) AppleWebKit/533.1 (KHTML, like Gecko) \
            Version/4.0 Mobile Safari/533.1",
        "Mozilla/5.0 (Linux; U; Android 2.3.3; zh-tw; HTC_Pyramid Build/GRI40) AppleWebKit/533.1 (KHTML, like Gecko) \
            Version/4.0 Mobile Safari",
        "Mozilla/5.0 (Linux; U; Android 2.3.3; zh-tw; HTC Pyramid Build/GRI40) AppleWebKit/533.1 (KHTML, like Gecko) \
            Version/4.0 Mobile Safari/533.1",
        "Mozilla/5.0 (Linux; U; Android 2.3.3; ko-kr; LG-LU3000 Build/GRI40) AppleWebKit/533.1 (KHTML, like Gecko) \
            Version/4.0 Mobile Safari/533.1",
        "Mozilla/5.0 (Linux; U; Android 2.3.3; en-us; HTC_DesireS_S510e Build/GRI40) AppleWebKit/533.1 (KHTML, like \
            Gecko) Version/4.0 Mobile Safari/533.1",
        "Mozilla/5.0 (Linux; U; Android 2.3.3; en-us; HTC_DesireS_S510e Build/GRI40) AppleWebKit/533.1 (KHTML, like \
            Gecko) Version/4.0 Mobile",
        "Mozilla/5.0 (Linux; U; Android 2.3.3; de-de; HTC Desire Build/GRI40) AppleWebKit/533.1 (KHTML, like Gecko) \
            Version/4.0 Mobile Safari/533.1",
        "Mozilla/5.0 (Linux; U; Android 2.3.3; de-ch; HTC Desire Build/FRF91) AppleWebKit/533.1 (KHTML, like Gecko) \
            Version/4.0 Mobile Safari/533.1",
        "Mozilla/5.0 (Linux; U; Android 2.2; fr-lu; HTC Legend Build/FRF91) AppleWebKit/533.1 (KHTML, like Gecko) \
            Version/4.0 Mobile Safari/533.1",
        "Mozilla/5.0 (Linux; U; Android 2.2; en-sa; HTC_DesireHD_A9191 Build/FRF91) AppleWebKit/533.1 (KHTML, like \
            Gecko) Version/4.0 Mobile Safari/533.1",
        "Mozilla/5.0 (Linux; U; Android 2.2.1; fr-fr; HTC_DesireZ_A7272 Build/FRG83D) AppleWebKit/533.1 (KHTML, like \
            Gecko) Version/4.0 Mobile Safari/533.1",
        "Mozilla/5.0 (Linux; U; Android 2.2.1; en-gb; HTC_DesireZ_A7272 Build/FRG83D) AppleWebKit/533.1 (KHTML, like \
            Gecko) Version/4.0 Mobile Safari/533.1",
        "Mozilla/5.0 (Linux; U; Android 2.2.1; en-ca; LG-P505R Build/FRG83) AppleWebKit/533.1 (KHTML, like Gecko) \
            Version/4.0 Mobile Safari/533.1",
        ]

    def __init__(self, user_agent=''):
        self.user_agent = user_agent

    def process_request(self, request, spider):
        ua = random.choice(self.user_agent_list)
        if ua:
            request.headers.setdefault('User-Agent', ua)


class BrowserRandomUserAgentMiddleware(UserAgentMiddleware):

    "pc浏览器serAgent"

    user_agent_list = [
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/22.0.1207.1 Safari/537.1",
        "Mozilla/5.0 (X11; CrOS i686 2268.111.0) AppleWebKit/536.11 (KHTML, like Gecko) Chrome/20.0.1132.57 Safari/536.11",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.6 (KHTML, like Gecko) Chrome/20.0.1092.0 Safari/536.6",
        "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.6 (KHTML, like Gecko) Chrome/20.0.1090.0 Safari/536.6",
        "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/19.77.34.5 Safari/537.1",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.9 Safari/536.5",
        "Mozilla/5.0 (Windows NT 6.0) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.36 Safari/536.5",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3",
        "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_0) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3",
        "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1062.0 Safari/536.3",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1062.0 Safari/536.3",
        "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3",
        "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3",
        "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3  (KHTML, like Gecko) Chrome/19.0.1061.0 Safari/536.3",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/535.24 (KHTML, like Gecko) Chrome/19.0.1055.1 Safari/535.24",
        "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/535.24 (KHTML, like Gecko) Chrome/19.0.1055.1 Safari/535.24",
    ]

    def __init__(self, user_agent=''):
        self.user_agent = user_agent

    def process_request(self, request, spider):
        ua = random.choice(self.user_agent_list)
        if ua:
            request.headers.setdefault('User-Agent', ua)
