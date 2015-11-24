# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class StartCityItem(scrapy.Item):
    city_id = scrapy.Field(serializer=int)
    city_name = scrapy.Field()
    alias_name = scrapy.Field()
    parent_id = scrapy.Field()
    short_name = scrapy.Field()
    full_name = scrapy.Field()
    en_name = scrapy.Field()
    provider = scrapy.Field(serializer=int)
    is_pre_sell = scrapy.Field(serializer=int)
    is_connected = scrapy.Field(serializer=int)


class TargetCityItem(scrapy.Item):
    carry_sta_id = scrapy.Field()
    carry_sta_name = scrapy.Field()
    stop_name = scrapy.Field()
    short_name = scrapy.Field()
    full_name = scrapy.Field()
    en_name = scrapy.Field()
    starting_city_id = scrapy.Field(serializer=int)


class LineItem(scrapy.Item):
    """
    Primary Key:  carry_sta_id, sign_id, stop_name, drv_date_time
    """
    carry_sta_id = scrapy.Field()
    carry_sta_name = scrapy.Field()
    city_id = scrapy.Field(serializer=int)
    city = scrapy.Field()
    sign_id = scrapy.Field()
    sch_id = scrapy.Field()
    drv_date_time = scrapy.Field()
    end_sta_name = scrapy.Field()
    full_price = scrapy.Field(serializer=float)
    half_price = scrapy.Field(serializer=float)
    amount = scrapy.Field(serializer=int)
    child_amount = scrapy.Field()
    sch_type_id = scrapy.Field(serializer=int)
    mile = scrapy.Field()
    extra_flag = scrapy.Field()
    bus = scrapy.Field()
    sch_type_name = scrapy.Field()
    bus_type_name = scrapy.Field()
    pass_id = scrapy.Field()
    mot_name = scrapy.Field()
    stop_name = scrapy.Field()
    stop_code = scrapy.Field()
    stop_alias_name = scrapy.Field()
    booking_url = scrapy.Field()
    stop_num = scrapy.Field()
    max_sell_num = scrapy.Field()
    is_insure = scrapy.Field(serializer=int)
    service_price = scrapy.Field()
