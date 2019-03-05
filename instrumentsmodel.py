import sys
import re
from pprint import pprint

from PyQt5.QtCore import (QFile, QLockFile, QFileInfo, QAbstractListModel, Qt,
                          QModelIndex, pyqtSlot, pyqtSignal, pyqtProperty, 
                          QObject)
from helpers import getFilePath, loadFromFile

class InstrumentsModel(QAbstractListModel):

    ModelData = Qt.UserRole + 1

    _roles = { ModelData: b"modelData" }

    insChanged = pyqtSignal()

    def __init__(self, parent=None):
        super(InstrumentsModel, self).__init__(parent)
        self._data = [{"Name": ""}]
        self._fileName = "instruments.json"
        self._populateData()


    def rowCount(self, parent=QModelIndex()):
        return len(self._data)


    def data(self, index, role):
        try:
            data = self._data[index.row()]
        except IndexError:
            return QVariant()

        if role == self.ModelData:
            return data["Name"]

        return QVariant()


    def roleNames(self):
        return self._roles


    def _populateData(self):
        file = getFilePath(self._fileName)
        data = loadFromFile(file)

        for x in data:
            self._data.append(x)


    def getInstrumentsName(self):
        name = []
        for d in self._data:
            name.append(d["Name"])
        return name


    def getInstrument(self, name):
        for i, d in enumerate(self._data):
            if name == d["Name"]:
                return self._data[i]


    @pyqtSlot(str, result=int)
    def getIndex(self, insId):
        for i, d in enumerate(self._data):
            if i == 0:
                continue
            if insId == d["ZMInstrumentID"]:
                return i
        return -1


    @pyqtSlot(str)
    def search(self, words):
        match = []
        for data in self._data:
            s = re.search("({}\w+)".format(words), data["Name"])

            if s:
                match.append(data["Name"])

        print(match)
                
            
            
    
