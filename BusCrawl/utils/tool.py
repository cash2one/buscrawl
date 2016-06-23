# -*- coding: utf-8 -*-

from pypinyin import pinyin
from scrapy.conf import settings
import pypinyin
import hashlib
import redis
import re

import cStringIO

try:
    import Image
    import ImageDraw
    import ImageFont
    import ImageFilter
except ImportError:
    from PIL import Image
    from PIL import ImageDraw
    from PIL import ImageFont
    from PIL import ImageFilter
from datetime import datetime as dte
from pytesseract import image_to_string


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


def trans_js_str(s):
    """
    {aa:'bb'} ==> {"aa":"bb"}
    """
    for k in set(re.findall("([A-Za-z]+):", s)):
        s = re.sub(r"\b%s\b" % k, '"%s"' % k, s)
    s = s.replace("'", '"')
    return s


def vcode_cqky(img_content):
    ims = cStringIO.StringIO(img_content)
    im = Image.open(ims)
    im = im.convert('L')
    im = im.point(lambda x: 255 if x > 140 else 0)
    im = ecp(im)
    code = image_to_string(im, lang='kp', config='-psm 8')
    return code


def ecp(im):
    frame = im.load()
    (w, h) = im.size
    for i in xrange(w):
        for j in xrange(h):
            if frame[i, j] != 255:
                count = 0
                try:
                    if frame[i, j - 1] == 255:
                        count += 1
                except IndexError:
                    pass
                try:
                    if frame[i, j + 1] == 255:
                        count += 1
                except IndexError:
                    pass
                try:
                    if frame[i - 1, j - 1] == 255:
                        count += 1
                except IndexError:
                    pass
                try:
                    if frame[i - 1, j] == 255:
                        count += 1
                except IndexError:
                    pass
                try:
                    if frame[i - 1, j + 1] == 255:
                        count += 1
                except IndexError:
                    pass
                try:
                    if frame[i + 1, j - 1] == 255:
                        count += 1
                except IndexError:
                    pass
                try:
                    if frame[i + 1, j] == 255:
                        count += 1
                except IndexError:
                    pass
                try:
                    if frame[i + 1, j + 1] == 255:
                        count += 1
                except IndexError:
                    pass
                if count >= 6:
                    frame[i, j] = 255
    return im
