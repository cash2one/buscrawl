# -*- coding:utf-8 -*-

import pymongo
import datetime

mongo_src = pymongo.MongoClient("mongodb://localhost:27017")
mongo_dest = pymongo.MongoClient("mongodb://localhost:27017")


def migrate():
    for d in mongo_src.scqcp.find({}):
        start_date, start_time = d["drv_date_time"].split(" ")
        new_data = {
            "scheduleId": "",
            "scheduleCode": d["sch_id"],
            "routeName": "",
            "startCityCode": d["city_id"],
            "startCityName": d["city"],
            "startStationCode": d["carry_sta_id"],
            "startStationName": d["carry_sta_name"],
            "endCityCode": "",
            "endCityName": d["stop_alias_name"].strip() and d["stop_name"],
            "endStationCode": "",
            "endStationName": d["end_sta_name"],
            "startDate": start_date,
            "startTime": start_time,
            "endDate": "",
            "endTime": "",
            "fromStationName": "",
            "fromStationCode": "",
            "reachStationName": "",
            "distance": d["miles"],
            "duration": "",
            "vehicleUnit": "",
            "fullPrice": d["full_price"],
            "halfPrice": d["half_price"],
            "vehicleTypeName": d["bus_type_name"],
            "seatType": "",
            "scheduleStatus": "",
            "totalSeats": "",
            "leaveSeats": "",
            "childLeaveSeats": "",
            "viaStation": "",
            "saleStates": "",
            "busId": d["bus"],
            "stId": "",
            "depotId": "",
            "royalty": "",
            "makeDate": "",
            "makeTime": "",
            "lockOfParking": "",
            "ticketEntrance": "",
            "fuelSurcharge": "",
            "zuoWeiChuan": "",
            "isSpecial": "",
            "lineType": "",
            "tingCheDao": "",
            "isLimit": "",
            "companyCode": "",
            "interfaceId": "",
            "busNumId": "",
            "extra_info": "",
            "date": datetime.datetime.now(),
        }

if __name__ == "__main__":
    migrate()
