#!/usr/bin/env python
# encoding: utf-8

import scrapy
import datetime
import urllib
from bs4 import BeautifulSoup as bs
import re
import requests
import json
from bs4 import BeautifulSoup

from datetime import datetime as dte
from BusCrawl.item import LineItem
from BusCrawl.utils.tool import get_pinyin_first_litter
from BusCrawl.utils.tool import get_redis
from base import SpiderBase


class Qdky(SpiderBase):
    name = "qdky"
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipeline.MongoPipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
            'BusCrawl.middleware.BrowserRandomUserAgentMiddleware': 400,
            'BusCrawl.middleware.QdkyProxyMiddleware': 410,
            'BusCrawl.middleware.QdkyHeaderMiddleware': 400,
        },
        # "DOWNLOAD_DELAY": 0.75,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
    }

    def get_init_dest_list(self):
        lst = [{"zdbm":'000025',"value":'HY海阳'},{"zdbm":'000028',"value":'LGZ留格庄'},{"zdbm":'000032',"value":'RS乳山'},{"zdbm":'000043',"value":'WD文登'},{"zdbm":'000051',"value":'RC荣城'},{"zdbm":'000057',"value":'LD俚岛'},
            {"zdbm":'000109',"value":'LY莱阳'},{"zdbm":'000116',"value":'QX栖霞'},{"zdbm":'000130',"value":'PL蓬莱'},{"zdbm":'000143',"value":'ZY招远'},{"zdbm":'000154',"value":'HC黄城'},{"zdbm":'000185',"value":'TY桃园'},
            {"zdbm":'000190',"value":'YT烟台'},{"zdbm":'000213',"value":'BS北墅'},{"zdbm":'000261',"value":'TC桃村'},{"zdbm":'000271',"value":'XJD徐家店'},{"zdbm":'000281',"value":'GC郭城'},{"zdbm":'000296',"value":'MP牟平'},
            {"zdbm":'000317',"value":'SD石岛'},{"zdbm":'000331',"value":'WH威海'},{"zdbm":'000341',"value":'LXD龙须岛'},{"zdbm":'000356',"value":'PD平度'},{"zdbm":'000368',"value":'LZ莱州'},{"zdbm":'000382',"value":'QJ七级'},
            {"zdbm":'000390',"value":'GM高密'},{"zdbm":'000395',"value":'SH沙河'},{"zdbm":'000401',"value":'WF潍坊'},{"zdbm":'000402',"value":'CL昌乐'},{"zdbm":'000403',"value":'QZ青州'},{"zdbm":'000405',"value":'ZB淄博'},
            {"zdbm":'000406',"value":'ZC周村'},{"zdbm":'000408',"value":'JN济南'},{"zdbm":'000413',"value":'LQ临清'},{"zdbm":'000420',"value":'HD邯郸'},{"zdbm":'000439',"value":'SG寿光'},{"zdbm":'000441',"value":'GR广饶'},
            {"zdbm":'000443',"value":'BZ滨州'},{"zdbm":'000445',"value":'WD无棣'},{"zdbm":'000447',"value":'LL乐陵'},{"zdbm":'000455',"value":'GT高唐'},{"zdbm":'000464',"value":'LC聊城'},{"zdbm":'000491',"value":'AQ安丘'},
            {"zdbm":'000501',"value":'LQ临朐'},{"zdbm":'000533',"value":'RZ日照'},{"zdbm":'000545',"value":'GY赣榆'},{"zdbm":'000547',"value":'XP新浦'},{"zdbm":'000553',"value":'FN阜宁'},{"zdbm":'000555',"value":'YC盐城'},
            {"zdbm":'000559',"value":'NT南通'},{"zdbm":'000582',"value":'WL五莲'},{"zdbm":'000597',"value":'JN莒南'},{"zdbm":'000598',"value":'BQ板泉'},{"zdbm":'000606',"value":'LS临沭'},{"zdbm":'000614',"value":'TC郯城'},
            {"zdbm":'000624',"value":'LS岚山'},{"zdbm":'000626',"value":'NJ南京'},{"zdbm":'000629',"value":'HZ湖州'},{"zdbm":'000630',"value":'HZ杭州'},{"zdbm":'000631',"value":'YW义乌'},{"zdbm":'000637',"value":'HF合肥'},
            {"zdbm":'000639',"value":'GY高邮'},{"zdbm":'000640',"value":'JD江都'},{"zdbm":'000641',"value":'HA淮安'},{"zdbm":'000644',"value":'JJ靖江'},{"zdbm":'000645',"value":'JY江阴'},{"zdbm":'000646',"value":'WX无锡'},
            {"zdbm":'000678',"value":'JX莒县'},{"zdbm":'000679',"value":'YZ扬州'},{"zdbm":'000693',"value":'LY临沂'},{"zdbm":'000702',"value":'CS苍山'},{"zdbm":'000710',"value":'ZZ枣庄'},{"zdbm":'000711',"value":'XC薛城'},
            {"zdbm":'000712',"value":'WS微山'},{"zdbm":'000714',"value":'PX沛县'},{"zdbm":'000715',"value":'FX丰县'},{"zdbm":'000716',"value":'SX单县'},{"zdbm":'000718',"value":'SQ商丘'},{"zdbm":'000727',"value":'TZ滕州'},
            {"zdbm":'000728',"value":'BZ亳州'},{"zdbm":'000735',"value":'XZ徐州'},{"zdbm":'000738',"value":'PX邳县'},{"zdbm":'000743',"value":'FX费县'},{"zdbm":'000745',"value":'PY平邑'},{"zdbm":'000758',"value":'YN沂南'},
            {"zdbm":'000776',"value":'MT孟疃'},{"zdbm":'000785',"value":'YS沂水'},{"zdbm":'000798',"value":'MY蒙阴'},{"zdbm":'000805',"value":'QF曲阜'},{"zdbm":'000807',"value":'JN济宁'},{"zdbm":'000808',"value":'JX金乡'},
            {"zdbm":'000809',"value":'JX嘉祥'},{"zdbm":'000811',"value":'HZ菏泽'},{"zdbm":'000812',"value":'DM东明'},{"zdbm":'000817',"value":'YC郓城'},{"zdbm":'000831',"value":'YY沂源'},{"zdbm":'000841',"value":'LW莱芜'},
            {"zdbm":'000849',"value":'TA泰安'},{"zdbm":'000857',"value":'XW新汶'},{"zdbm":'000859',"value":'CS常熟'},{"zdbm":'000872',"value":'AY安阳'},{"zdbm":'000873',"value":'BS博山'},{"zdbm":'000890',"value":'DY东营'},
            {"zdbm":'000903',"value":'CY昌邑'},{"zdbm":'000913',"value":'XH仙河'},{"zdbm":'000916',"value":'KF开封'},{"zdbm":'000917',"value":'ZZ郑州'},{"zdbm":'000920',"value":'HM惠民'},{"zdbm":'000921',"value":'SH商河'},
            {"zdbm":'000925',"value":'TZ田庄'},{"zdbm":'000928',"value":'FC肥城'},{"zdbm":'000941',"value":'FC风城'},{"zdbm":'000944',"value":'NJ宁津'},{"zdbm":'000948',"value":'DZ德州'},{"zdbm":'000949',"value":'YX阳信'},
            {"zdbm":'000962',"value":'LS丽水'},{"zdbm":'000963',"value":'WZ温州'},{"zdbm":'000964',"value":'ZJ镇江'},{"zdbm":'000968',"value":'TZ泰州'},{"zdbm":'000984',"value":'ZZ庄寨'},{"zdbm":'000987',"value":'TEZ台儿庄'},
            {"zdbm":'000991',"value":'XY新沂'},{"zdbm":'001003',"value":'CZ沧州'},{"zdbm":'001006',"value":'HJ河间'},{"zdbm":'001011',"value":'BD保定'},{"zdbm":'001012',"value":'XJ夏津'},{"zdbm":'001020',"value":'SJZ石家庄'},
            {"zdbm":'001025',"value":'PY濮阳'},{"zdbm":'001028',"value":'YT鱼台'},{"zdbm":'001029',"value":'ZQ章丘'},{"zdbm":'001032',"value":'XX新乡'},{"zdbm":'001040',"value":'BJ北京'},{"zdbm":'001059',"value":'HN淮南'},
            {"zdbm":'001069',"value":'XT邢台'},{"zdbm":'001073',"value":'SX绍兴'},{"zdbm":'001079',"value":'HK汉口'},{"zdbm":'001083',"value":'RA瑞安'},{"zdbm":'001096',"value":'QH齐河'},{"zdbm":'001097',"value":'YC禹城'},
            {"zdbm":'001100',"value":'SZ苏州'},{"zdbm":'001101',"value":'JX嘉兴'},{"zdbm":'001105',"value":'WL温岭'},{"zdbm":'001107',"value":'CZ常州'},{"zdbm":'001109',"value":'LG龙港'},{"zdbm":'001113',"value":'BX白象'},
            {"zdbm":'001116',"value":'LD楼德'},{"zdbm":'001134',"value":'MAS马鞍山'},{"zdbm":'001136',"value":'WH芜湖'},{"zdbm":'001149',"value":'NY宁阳'},{"zdbm":'001155',"value":'ZK周口'},{"zdbm":'001160',"value":'NY南阳'},
            {"zdbm":'001163',"value":'SH上海'},{"zdbm":'001168',"value":'SN睢宁'},{"zdbm":'001173',"value":'SY射阳'},{"zdbm":'001183',"value":'XY襄阳'},{"zdbm":'001184',"value":'JM荆门'},{"zdbm":'001187',"value":'ST水头'},
            {"zdbm":'001188',"value":'YY余姚'},{"zdbm":'001203',"value":'GQ高青'},{"zdbm":'001210',"value":'NB宁波'},{"zdbm":'001216',"value":'AQ安庆'},{"zdbm":'001239',"value":'TJ天津'},{"zdbm":'001260',"value":'PT莆田'},
            {"zdbm":'001264',"value":'SS石狮'},{"zdbm":'001265',"value":'SQ沈丘'},{"zdbm":'001269',"value":'JH建湖'},{"zdbm":'001283',"value":'JC鄄城'},{"zdbm":'001297',"value":'TY太原'},{"zdbm":'001304',"value":'JY靖宇'},
            {"zdbm":'001308',"value":'DH东海'},{"zdbm":'001310',"value":'SWD沙窝岛'},{"zdbm":'001313',"value":'DN戴南'},{"zdbm":'001326',"value":'CW成武'},{"zdbm":'001334',"value":'JJ九江'},{"zdbm":'001345',"value":'TL铜陵'},
            {"zdbm":'001356',"value":'ZH沾化'},{"zdbm":'001358',"value":'SMX三门峡'},{"zdbm":'001361',"value":'XA西安'},{"zdbm":'001374',"value":'RD如东'},{"zdbm":'001387',"value":'SP凇浦'},{"zdbm":'001401',"value":'LZ临淄'},
            {"zdbm":'001410',"value":'DP东平'},{"zdbm":'001422',"value":'XG墟沟'},{"zdbm":'001430',"value":'ZMD驻马店'},{"zdbm":'001431',"value":'SY沈阳'},{"zdbm":'001444',"value":'SZ寿张'},{"zdbm":'001446',"value":'HS衡水'},
            {"zdbm":'001450',"value":'CZ长治'},{"zdbm":'001452',"value":'JH金华'},{"zdbm":'001453',"value":'YZ扬中'},{"zdbm":'001477',"value":'CF赤峰'},{"zdbm":'001481',"value":'CZQ楚州区'},{"zdbm":'001488',"value":'GX冠县'},
            {"zdbm":'001491',"value":'CY长垣'},{"zdbm":'001495',"value":'YZ禹州'},{"zdbm":'001499',"value":'LF临汾'},{"zdbm":'001500',"value":'YY岳阳'},{"zdbm":'001527',"value":'ZS舟山'},{"zdbm":'001531',"value":'BT包头'},
            {"zdbm":'001548',"value":'XM厦门'},{"zdbm":'001549',"value":'SJZ邵家庄'},{"zdbm":'001550',"value":'WJZZ王家庄子'},{"zdbm":'001551',"value":'CC昌城'},{"zdbm":'001552',"value":'CS赤山'},
            {"zdbm":'001553',"value":'DJW大家洼'},{"zdbm":'001554',"value":'GGZ高戈庄'},{"zdbm":'001555',"value":'JG井沟'},{"zdbm":'001556',"value":'XZ相州'},{"zdbm":'001557',"value":'KJ阚家'},
            {"zdbm":'001585',"value":'ZP邹平'},{"zdbm":'001596',"value":'YT烟台西站'},{"zdbm":'001601',"value":'SS沙市'},{"zdbm":'001603',"value":'JC晋城'},{"zdbm":'001604',"value":'CD常德'},{"zdbm":'001607',"value":'CD成都'},
            {"zdbm":'001608',"value":'BZ巴中'},{"zdbm":'001609',"value":'LH临河'},{"zdbm":'001613',"value":'HM侯马'},{"zdbm":'001616',"value":'ST山亭'},{"zdbm":'001617',"value":'CQ重庆'},{"zdbm":'001625',"value":'CS长沙'},
            {"zdbm":'001628',"value":'BS白山'},{"zdbm":'001632',"value":'DZ定州'},{"zdbm":'001633',"value":'GBD高碑店'},{"zdbm":'001642',"value":'NC南昌'},{"zdbm":'001645',"value":'ZQ中桥'},{"zdbm":'001649',"value":'JL吉林'},
            {"zdbm":'001650',"value":'CC长春'},{"zdbm":'001657',"value":'HQP黄旗堡'},{"zdbm":'001666',"value":'DP德平'},{"zdbm":'001672',"value":'NP南皮'},{"zdbm":'001673',"value":'PY平原'},{"zdbm":'001674',"value":'YTY樱桃园'},
            {"zdbm":'001677',"value":'ZC邹城'},{"zdbm":'001691',"value":'YJ延吉'},{"zdbm":'001692',"value":'HEB哈尔滨'},{"zdbm":'001693',"value":'QHD秦皇岛'},{"zdbm":'001694',"value":'LWC老武城'},
            {"zdbm":'001695',"value":'HB鹤壁'},{"zdbm":'001696',"value":'XY夏邑'},{"zdbm":'001697',"value":'SL石莱'},{"zdbm":'001700',"value":'DT定陶'},{"zdbm":'001716',"value":'YL榆林'},{"zdbm":'001845',"value":'BY泌阳'},
            {"zdbm":'001848',"value":'NN南宁'},{"zdbm":'001859',"value":'KM昆明'},{"zdbm":'001864',"value":'TL通辽'},{"zdbm":'001870',"value":'LJ庐江'},{"zdbm":'001874',"value":'QY庆阳'},{"zdbm":'001892',"value":'JT金坛'},
            {"zdbm":'001910',"value":'YB宜宾'},{"zdbm":'001922',"value":'YS榆树'},{"zdbm":'001734',"value":'NJ南江'},{"zdbm":'001744',"value":'JZ金寨'},{"zdbm":'001746',"value":'TH太和'},{"zdbm":'001803',"value":'JX鸡西'},
            {"zdbm":'001812',"value":'YC运城'},{"zdbm":'001817',"value":'SZ嵊州'},{"zdbm":'000105',"value":'LX莱西'},{"zdbm":'000518',"value":'JN胶南'},{"zdbm":'000662',"value":'ZC诸城'},{"zdbm":'000810',"value":'JY巨野'},
            {"zdbm":'000816',"value":'LS梁山'},{"zdbm":'000856',"value":'XT新泰'},{"zdbm":'000875',"value":'ZC淄川'},{"zdbm":'001086',"value":'CX曹县'},{"zdbm":'001274',"value":'QK青口'},{"zdbm":'002159',"value":'SYH世园会往返'},
            {"zdbm":'160356',"value":'PD平度(优)'},{"zdbm":'160105',"value":'LX莱西(优)'},{"zdbm":'000007',"value":'JM即墨'},{"zdbm":'001293',"value":'BLY百龄园'},{"zdbm":'000993',"value":'SQ宿迁'},
            {"zdbm":'001885',"value":'QDGS青岛'},{"zdbm":'001001',"value":'QDDZ青岛东站'},{"zdbm":'001547',"value":'HBH海泊河'},{"zdbm":'001924',"value":'CS茶山'},{"zdbm":'002198',"value":'ZMS藏马山'},
            {"zdbm":'002215',"value":'SLR石老人'},{"zdbm":'002216',"value":'TDW唐岛湾'},{"zdbm":'001827',"value":'JY济阳'}]
        return lst
        
        r = get_redis()
        rds_key = "qdky_end_station"
        lst = r.get(rds_key)
        if not lst:
            end_station_list = []
            url = "http://ticket.qdjyjt.com/Scripts/destination.js"
            r = requests.get(url, headers={"User-Agent": "Chrome/51.0.2704.106"})
            res = r.content()
            for res_list in res['data']:
                end_station_list.append(res_list['name'])
            dest_str = json.dumps(lst)
            r.set(rds_key, dest_str)
        lst = json.loads(dest_str)
        return lst

    def start_requests(self):
        url = "http://ticket.qdjyjt.com/"
        return [scrapy.Request(url, callback=self.parse_start_city)]

    def parse_start_city(self, response):
        soup = BeautifulSoup(response.body, "lxml")
        print response.body
        params = {
            "__EVENTARGUMENT": soup.select("#__EVENTARGUMENT")[0].get("value"),
            "__EVENTTARGET": soup.select("#__EVENTTARGET")[0].get("value"),
            "__EVENTVALIDATION": soup.select("#__EVENTVALIDATION")[0].get("value"),
            "__VIEWSTATE": soup.select("#__VIEWSTATE")[0].get("value"),
        }
        url = "http://ticket.qdjyjt.com/"
        STATION_INFO = {
            '1.青岛站    ': ("青岛","青岛长途汽车站"),
            '2.沧口汽车站': ("青岛","青岛沧口汽车站"),
            '3.青岛西站  ': ("青岛","青岛西站"),
            'B.青岛北站  ': ("青岛","青岛汽车北站"),
            'C.青岛海泊河': ("青岛","青岛海泊河汽车站"),
            'D.青岛东站  ': ("青岛","青岛汽车东站"),
            'F.利津路站  ': ("青岛","青岛利津路汽车站"),
            'E.华联火车站': ("青岛","华联火车站"),
            'A.黄岛开发区': ("黄岛","黄岛汽车站"),
            '5.胶州汽车站': ("胶州","胶州汽车站"),  # 胶州
            '8.胶南汽车站': ("胶南","胶南汽车站"),  #胶南
            '4.即墨汽车站': ("即墨","即墨汽车站"), # 即墨
            '7.莱西汽车站': ("莱西","莱西汽车站"), # 莱西
            '9.平度汽车站': ("平度","平度汽车站"), # 平度
        }
        today = datetime.date.today()
        dest_list = self.get_init_dest_list()
        for s_station_name, (city_name, station_name) in STATION_INFO.items():
            if not self.is_need_crawl(city=station_name):
                continue
            for d in dest_list:
                name, dest_id = d["value"], d["zdbm"]
                end = {"city_name": name, 'city_id': dest_id}
                today = datetime.date.today()
                for j in range(1, 3):
                    sdate = str(today+datetime.timedelta(days=j))
                    if self.has_done(station_name, end['city_name'], sdate):
                        self.logger.info("ignore %s ==> %s %s" % (station_name, end['city_name'],sdate))
                        continue
                    data = {}
                    data.update(params)
                    data.update({
                        'ctl00$ContentPlaceHolder1$DropDownList3': unicode(s_station_name),
                        'ctl00$ContentPlaceHolder1$chengchezhan_id': '',
                        'destination-id': unicode(end['city_id']),
                        'ctl00$ContentPlaceHolder1$mudizhan_id': '',
                        'tripDate': unicode(sdate.replace('-', '/')),
                        'ctl00$ContentPlaceHolder1$chengcheriqi_id': '',
                        'ctl00$ContentPlaceHolder1$chengcheriqi_id0': '',
                        'ctl00$ContentPlaceHolder1$Button_1_cx': u'车次查询',
                    })
                    yield scrapy.FormRequest(url,
                                             method="POST",
                                             formdata=data,
                                             callback=self.parse_line,
                                             meta={"city_name": city_name,
                                                   "station_name": station_name,
                                                   "s_station_name": s_station_name,
                                                   "end": end, "date": sdate
                                                   }
                                            )


#     # 初始化到达城市
#     def parse_dcity(self, response):
#         s_city_name = response.meta['s_city_name'].decode('utf-8')
#         soup = response.body.split('[')[-1].split(']')[0]
#         info = soup.split('}')
#         data = {'s_city_name': s_city_name}
#         for x in info:
#             try:
#                 for y in self.sta_info.values():
#                     tmp = x.split("'")
#                     end = tmp[-2].decode('utf-8')
#                     p = re.compile(r'\w*', re.L)
#                     end = p.sub('', end)
#                     data['end'] = end
#                     data['end_id'] = tmp[1]
#                     data['start'] = y
#                     print data['end'], data['end_id']
#                     if len(tmp) != 5:
#                         continue
#                     if city.find({'end': data['end'], 'start': data['start']}).count() <= 0:
#                         city.save(dict(data))
#             except:
#                 pass

    def parse_line(self, response):
        city_name = response.meta['city_name']
        station_name = response.meta['station_name']
        s_station_name = response.meta['s_station_name']
        end = response.meta['end']
        sdate = response.meta['date']
        self.mark_done(station_name, end['city_name'], sdate)
        soup = bs(response.body, 'lxml')
        scl_list = soup.find('table', attrs={'id': 'ContentPlaceHolder1_GridViewbc'})
        if not scl_list:
            return
        if scl_list:
            scl_list = scl_list.find_all('tr', attrs={'style': True})
        for x in scl_list[1:]:
            y = x.find_all('td')
            ticket_status = y[3].get_text().strip()
            s_d_city_name = end['city_name']
            d_city_name = re.sub("[A-Za-z]", "", s_d_city_name)
            if ticket_status == u"有票":
                drv_date = sdate
                bus_num = y[1].get_text().strip()
                drv_time = y[2].get_text().strip()
                distance = y[4].get_text().strip()
                vehicle_type = y[5].get_text().strip().decode('utf-8')
                full_price = y[6].get_text().strip()
                s_sta_name = y[7].get_text().strip()
                attrs = dict(
                    s_province='山东',
                    s_city_id="",
                    s_city_name=city_name,
                    s_city_code=get_pinyin_first_litter(unicode(city_name)),
                    s_sta_name=station_name,
                    s_sta_id='',
                    d_city_name=d_city_name,
                    d_city_id=end['city_id'],
                    d_city_code=get_pinyin_first_litter(unicode(d_city_name)),
                    d_sta_id='',
                    d_sta_name=s_sta_name,
                    drv_date=drv_date,
                    drv_time=drv_time,
                    drv_datetime=dte.strptime("%s %s" % (drv_date, drv_time), "%Y-%m-%d %H:%M"),
                    distance=distance,
                    vehicle_type=vehicle_type,
                    seat_type="",
                    bus_num=bus_num,
                    full_price=float(full_price),
                    half_price=float(full_price) / 2,
                    fee=0,
                    crawl_datetime=dte.now(),
                    extra_info={'s_station_name': s_station_name, 's_d_city_name':s_d_city_name},
                    left_tickets=45,
                    crawl_source="qdky",
                    shift_id="",
                )
                yield LineItem(**attrs)

