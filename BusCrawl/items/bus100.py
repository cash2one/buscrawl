# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class StartCityItem(scrapy.Item):
    province_id = scrapy.Field(serializer=int)
    province_name = scrapy.Field()
    city_id = scrapy.Field(serializer=int)
    city_name = scrapy.Field()
    city_short_name = scrapy.Field()
    start_city_name = scrapy.Field()
    start_city_id = scrapy.Field()
    start_full_name = scrapy.Field()
    start_short_name = scrapy.Field()


class TargetCityItem(scrapy.Item):
    starting_id = scrapy.Field()
    target_name = scrapy.Field()
    short_name = scrapy.Field()
    full_name = scrapy.Field()


class LineItem(scrapy.Item):
    line_id = scrapy.Field()
    province_id = scrapy.Field(serializer=int)
    province_name = scrapy.Field()
    city_name = scrapy.Field()
    city_id = scrapy.Field()
    start_city_name = scrapy.Field()
    start_city_id = scrapy.Field()
    target_city_name = scrapy.Field()
#     target_city_id = scrapy.Field()
    departure_time = scrapy.Field()
    price = scrapy.Field()
    banci = scrapy.Field()
    distance = scrapy.Field()
    flag = scrapy.Field(serializer=int)
    shiftid = scrapy.Field()
    crawl_time = scrapy.Field()
