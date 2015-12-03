# -*-coding:utf-8-*-


class HeaderMiddleware(object):

    def process_request(self, request, spider):
        request.headers.setdefault("Content-Type", "application/json; charset=UTF-8")
        request.headers.setdefault("Authorization", "04b8cef68ef4f2d785150eb671999834")
#         request.meta['proxy'] = "http://192.168.1.47:8888"

