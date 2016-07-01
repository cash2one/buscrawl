# -*- coding: utf-8 -*-

from pypinyin import pinyin
from scrapy.conf import settings
import pypinyin
import hashlib
import redis


def get_pinyin_first_litter(hanzi):
    pinyin_list = pinyin(hanzi, style=pypinyin.FIRST_LETTER)
    pinyin_st = ''
    for i in pinyin_list:
        pinyin_st += i[0]
    return pinyin_st


def md5(msg):
    md5 = hashlib.md5(msg.encode('utf-8')).hexdigest()
    return md5

redis_list = {}


def get_redis(db=0):
    global redis_list
    if db not in redis_list:
        redis_conf = settings["REDIS_CONFIG"]
        host = redis_conf["host"]
        port = redis_conf["port"]
        r = redis.StrictRedis(host=host, port=port, db=db)
        redis_list[db] = r
    return redis_list[db]
