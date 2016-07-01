# -*- coding: utf-8 -*-
import scrapy


class LineItem(scrapy.Item):
    # 出发
    s_province = scrapy.Field()
    s_city_id = scrapy.Field()
    s_city_name = scrapy.Field()
    s_sta_name = scrapy.Field()
    s_sta_id = scrapy.Field()
    s_city_code = scrapy.Field()

    # 到达
    d_city_name = scrapy.Field()
    d_city_id = scrapy.Field()
    d_sta_name = scrapy.Field()
    d_sta_id = scrapy.Field()
    d_city_code = scrapy.Field()

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
    crawl_source = scrapy.Field()
    shift_id = scrapy.Field()

    def valid(self):
        # 必须有值的属性
        required_attrs = ["s_province",
                          "s_city_name",
                          "s_city_code",
                          "s_sta_name",
                          "d_city_name",
                          "d_city_code",]
        for attr in required_attrs:
            if not self[attr]:
                return "%s required" % attr
        return ""
