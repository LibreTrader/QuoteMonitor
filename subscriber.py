import json
import logging

from uuid import uuid4
from pprint import pprint
from asyncio import ensure_future as create_task

from PyQt5.QtCore import pyqtSlot, QObject


L = logging.getLogger(__name__)


class Subscriber(QObject):

    def __init__(self, dealer, quoteModel, parent=None):
        super(Subscriber, self).__init__(parent)
        self.quoteModel = quoteModel
        self._dealer = dealer
        self._ins = set()


    # def addInstrument(self, row, ins):
    #     if "ZMInstrumentID" in ins:
    #         insId = ins["ZMInstrumentID"]

    #         if insId not in self._ins:
    #             self._ins.append(insId)
    #             self.subscribe(ins)

    #         self.quoteModel.addInsToRow(row, insId)


    def subscribe(self, ins):
        if ins["ZMInstrumentID"] in self._ins:
            return
        msg = {}
        msg["Header"] = header = {}
        header["MsgType"] = "V"
        header["ZMEndpoint"] = ins["ZMEndpoint"]
        
        msg["Body"] = body = {}
        body["ZMInstrumentID"] = ins["ZMInstrumentID"]
        body["SubscriptionRequestType"] = "1"
        body["MDReqGrp"] = "*"
        body["MDReqID"] = "quotemonitor"
        body["MarketDepth"] = 1
        self._ins.add(ins["ZMInstrumentID"])
        L.debug("subscribing to {}@{} ..."
                .format(ins["ZMInstrumentID"], ins["ZMEndpoint"]))

        create_task(self.sendMessage(msg))


    def unsubscribe(self, ins):
        pprint(ins)
        msg = {}
        msg["Header"] = header = {}
        header["MsgType"] = "V"
        header["ZMEndpoint"] = ins["ZMEndpoint"]

        msg["Body"] = body = {}
        body["ZMInstrumentID"] = ins["ZMInstrumentID"]
        body["SubscriptionRequestType"] = "2"
        body["MDReqGrp"] = "*"
        body["MDReqID"] = "quotemonitor"
        
        pprint(msg)
        create_task(self.sendMessage(msg))


    async def sendMessage(self, msg):
        msg = (" " + json.dumps(msg)).encode()
        msgParts = [b"", str(uuid4()).encode(), msg]
        self._dealer.send_multipart(msgParts)
        res = await self._dealer.recv_multipart()

        # print(res)


    def marketDataReceived(self, msgType, endpoint, msg):
        body = msg["Body"]
        if msgType == "W":
            insId = body["ZMInstrumentID"]
            if insId not in self._ins:
                return

            data = body["MDFullGrp"]
            for d in data:
                self.quoteModel.update(insId, endpoint, d)

        elif msgType == "X":
            updates = body["MDIncGrp"]

            for x in updates:
                insId = x["ZMInstrumentID"]
                if insId not in self._ins:
                    return
                action = x["MDUpdateAction"]
                if action != "2":
                    self.quoteModel.update(insId, endpoint, x)






