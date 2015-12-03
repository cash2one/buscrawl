# -*- coding: utf-8 -*-

from pypinyin import pinyin
import pypinyin


def get_pinyin_first_litter(hanzi):
    pinyin_list = pinyin(hanzi, style=pypinyin.FIRST_LETTER)
    pinyin_st = ''
    for i in pinyin_list:
        pinyin_st += i[0]
    return pinyin_st
