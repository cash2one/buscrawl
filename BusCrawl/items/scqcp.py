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
    json_str_hash = scrapy.Field()
    json_str = scrapy.Field()
