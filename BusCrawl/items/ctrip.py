# -*- coding: utf-8 -*-

import scrapy


class LineItem(scrapy.Item):
    # 出发
    s_province = scrapy.Field()
    s_city_name = scrapy.Field()
    s_city_pinyin = scrapy.Field()
    s_city_short_pinyin = scrapy.Field()
    s_sta_name = scrapy.Field()
    s_sta_pinyin = scrapy.Field()
    s_sta_short_pinyin = scrapy.Field()

    # 到达
    d_city_name = scrapy.Field()
    d_city_pinyin = scrapy.Field()
    d_city_short_pinyin = scrapy.Field()
    d_sta_name = scrapy.Field()
    d_sta_pinyin = scrapy.Field()
    d_sta_short_pinyin = scrapy.Field()

    line_id = scrapy.Field()
    drv_date = scrapy.Field()
    drv_time = scrapy.Field()
    drv_datetime = scrapy.Field()
    distance = scrapy.Field()
    vehicle_type = scrapy.Field()
    seat_type = scrapy.Field()
    bus_num = scrapy.Field()
    full_price = scrapy.Field(serializer=float)
    half_price = scrapy.Field(serializer=float)
    fee = scrapy.Field(serializer=float)
    crawl_datetime = scrapy.Field()
    extra_info = scrapy.Field()
    left_tickets = scrapy.Field(serializer=int)
