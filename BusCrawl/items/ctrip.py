# -*- coding: utf-8 -*-

import scrapy

class StartItem(scrapy.Item):
    hash_key = scrapy.Field()
    province = scrapy.Field()
    name = scrapy.Field()
    pinyin = scrapy.Field()
    short_pinyin = scrapy.Field()


class TargetItem(scrapy.Item):
    name = scrapy.Field()
    pinyin = scrapy.Field()
    short_pinyin = scrapy.Field()


class LineItem(scrapy.Item):
    pass
