# -*-coding:utf-8-*-


class HeaderMiddleware(object):

    def process_request(self, request, spider):
        request.headers.setdefault("Content-Type", "application/json; charset=UTF-8")
        request.headers.setdefault("Authorization", "04b8cef68ef4f2d785150eb671999834")
        request.headers.setdefault("X-Requested-With", "ctrip.android.view")
