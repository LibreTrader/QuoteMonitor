import sys
import json
import asyncio
import zmq.asyncio
import ipdb
import utils.logging
import logging
import os

from math import ceil
from pprint import pprint, pformat
from collections import defaultdict
from quamash import QEventLoop, QThreadExecutor
from asyncio import ensure_future as create_task

from helpers import *
from subscriber import Subscriber
from instrumentsmodel import InstrumentsModel

from PyQt5.QtCore import (Qt, QEvent, QAbstractTableModel, QModelIndex, QVariant,
                        QDir, QRect, QSize, QMimeData, QRect, QPoint)
from PyQt5.QtWidgets import (QApplication, QDialog, QTableView, QLineEdit,
                        QMainWindow, QCompleter, QStyledItemDelegate, QTextEdit,
                        QLabel, QAbstractItemView, QHeaderView, QSizePolicy,
                        QMenu, QAction, QMenuBar, QDialogButtonBox,
                        QVBoxLayout, QGroupBox, QCheckBox, QLabel,
                        QStyleOption, QProxyStyle)
from PyQt5.QtGui import QBrush, QColor, QPen


################################ GLOBALS ######################################

class GlobalState:
    pass
g = GlobalState()

L = logging.root

COLUMN_NAME = {
    "instrument": "Instrument",
    "bidPrice": "Bid Price",
    "bidSize": "Bid Size",
    "askPrice": "Ask Price",
    "askSize": "Ask Size",
    "lastPrice": "Last Price",
    "lastSize": "Last Size"
}

g.stateFile = "state.json"
g.state = None
g.colEditable = 0

###############################################################################


class QuoteModel(QAbstractTableModel):
    
    StringValueRole = Qt.UserRole + 1
    DataTypeRole = Qt.UserRole + 2
    TickDirectionRole = Qt.UserRole + 3

    _roles = {
        StringValueRole: b"stringValue",
        DataTypeRole: b"dataType",
        TickDirectionRole: b"tickDirection",
    }
    
    DND_MIME_TYPE = "application/libretrader-quotemon-table-index"

    def __init__(self, parent=None):
        super(QuoteModel, self).__init__(parent)

        self._rows = []
        self._cols = [ 
            "instrument",
            "bidPrice",
            "bidSize",
            "askPrice",
            "askSize",
            "lastPrice",
            "lastSize",
        ]
        self._data = defaultdict(dict)
        
        if g.state: 
            table = g.state["table"]
            rows = table["rows"]
            columns = table["columns"]
            data = table["data"]

            # self.updateColumns(columns)
            self._cols = columns
            self._rows = [tuple(x) if x else x for x in rows]
            self._data.update({eval(k): v for k, v in data.items()})
            
            # for v in self._data.values():
            #     name = v["instrument"]
            #     instrument = g.insModel.getInstrument(name)
            #     g.subscriber.subscribe(instrument)
        # model.addInsToRow(row, name, instrument)


            # for i, row in enumerate(rows):
            #     if row:
            #         print(row)
            #         # self._rows.insert(row[0], row[1])
            #     else:
            #         self._rows.insert(i, row)


    def restoredSubscription(self):
        if g.state:
            for v in self._data.values():
                name = v["instrument"]
                instrument = g.insModel.getInstrument(name)
                g.subscriber.subscribe(instrument)


    def columnCount(self, parent=None):
        return len(self._cols)
        # return 4


    def rowCount(self, parent=None):
        return len(self._rows)
        # return 4


    def columnName(self, index):
        return self._cols[index]


    def data(self, index, role):
        # print(index.row(), index.column(), role)
        # print(type(role), type(self.StringValueRole))
        # print(self._rows)
        row = index.row()
        col = index.column()
        field = self._cols[col]
        insKey = self._rows[row]
        ## print(f'field: {field} insId: {insId} data: {self._data}')
        #if role == self.DataTypeRole:
        #    if field == "instrument":
        #        return "instrumentCombo"
        #    if field in ("bidPrice", "askPrice", "lastPrice"):
        #        return "tickerPrice"
        #    else:
        #        return "string"
        #if role == self.StringValueRole:
        #    print(f"get data from {role}")
        #    if insId is None:
        #        return ""
        #    return self._data[insId].get(field, "")
        #if role == self.TickDirectionRole:
        #    key = field + "TickDirection"
        #    return self._data[insId].get(key, True)
        if role == Qt.DisplayRole:
            if insKey is not None:
                # print(self._data[insKey])
                # print(insKey, field)
                return QVariant(self._data[insKey].get(field, ""))
            # return "test"
        elif role == Qt.ForegroundRole:
            key = field + "TickDirection"
            val = self._data[insKey].get(key, 0)
            if val == 1:
                return QBrush(QColor("#698476"))
            if val == -1:
                return QBrush(QColor("#CD5362"))
            if col == g.colEditable:
                return QBrush(QColor("#000000"))
            else:
                return QBrush(Qt.white)
        elif role == Qt.BackgroundRole:
            if col == g.colEditable:
                color = QColor("#C8A355")
                if row % 2 == 0:
                    return QBrush(QColor.darker(color, 120)) 
                return QBrush(color)
        elif role == Qt.TextAlignmentRole:
            if col != g.colEditable:
                return Qt.AlignRight | Qt.AlignVCenter
        
        return QVariant()


    def dropMimeData(self, mime, action, row, col, parent):
        # print("formats: {}, action: {}, row: {}, col: {}"
        #       .format(mime.data(self.DND_MIME_TYPE), action, row, col))
        if row == -1:
            return True
        self.moveRow(int(mime.data(self.DND_MIME_TYPE)), row)
        
        return True


    def moveRow(self, fromRow, toRow):
        if fromRow == toRow:
            return
        self.beginResetModel()
        if toRow > fromRow:
            self._rows.insert(toRow, self._rows[fromRow])
            del self._rows[fromRow]
        else:
            self._rows.insert(toRow, self._rows[fromRow])
            del self._rows[fromRow + 1]
        self.endResetModel()


    def mimeData(self, indices):
        mime = QMimeData()
        idx = str(indices[0].row()).encode()
        mime.setData(self.DND_MIME_TYPE, idx)

        return mime


    def mimeTypes(self):
        return [self.DND_MIME_TYPE]


    def supportedDropActions(self):
        return Qt.MoveAction

    
    def flags(self, index):
        fl = Qt.NoItemFlags
        if index.isValid():
            fl |= Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled
            if index.column() == g.colEditable:
                fl |= Qt.ItemIsEditable
        else:
            fl |= Qt.ItemIsDropEnabled

        return fl


    def headerData(self, section, orientation, role):
        # print(f"section {section}, or: {orientientation}, role: {role}")
        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                return COLUMN_NAME.get(self._cols[section], "")
        if orientation == Qt.Vertical:
            if role == Qt.DisplayRole:
                return "test"
        return QVariant()
            #print(locals())
            #if section < 0 or section >= len(self._cols):
            #    return ""
            # for i, _ in enumerate(self._cols):
            #     print(f"{section}, {i}")
            #     if section == i:
            #         return self._cols[i]

    def updateColumns(self, cols):
        self.beginResetModel()
        self._cols = [x for x in self._cols if x in cols]
        for col in cols:
            if col not in self._cols:
                self._cols.append(col)
        self.endResetModel()


    def getColumns(self):
        return self._cols


    def getRows(self):
        return self._rows


    def appendRow(self):
        self.insertEmptyRow(self.rowCount())


    def removeRow(self, row):
        self.beginRemoveRows(QModelIndex(), row, row)
        ins_tuple = self._rows.pop(row)

        if ins_tuple not in self._rows:
            ins = g.insModel.getInstrument(ins_tuple[0])
            if ins is not None:
                g.subscriber.unsubscribe(ins)

        self.endRemoveRows()


    # @pyqtSlot(int, result=str)
    # def getInstrument(self, row):
    #     res = self._rows[row]
    #     return "" if res is None else res


    def insertEmptyRow(self, index):
        # self.beginInsertRows(QModelIndex(), index, index)
        # self._rows.insert(index, None)
        # self.endInsertRows()
        self.beginResetModel()
        self._rows.insert(index, None)
        self.endResetModel()
        

    def roleNames(self):
        return self._roles


    def addInsToRow(self, row, insName, insData):
        insKey = (insData["ZMInstrumentID"], insData["ZMEndpoint"])
        self._rows[row] = insKey
        if insKey not in self._data:
            self._data[insKey] = {"instrument": insName}
        self.dataChanged.emit(self.createIndex(row, 0),
                    self.createIndex(row, self.columnCount()))


    def updateSnapshot(self, ins, data, action):
        return
        #pprint(data)
        #et = data["MDEntryType"]
        #print("EntryType: ", et) 

       #  if et == "1":
       #      price = data["MDEntryPx"]


    def update(self, insId, endpoint, msg):
        et = msg["MDEntryType"]
        price = msg["MDEntryPx"]
        size = msg["MDEntrySize"]
        insKey = (insId, endpoint)
        data = self._data[insKey]
        
        if data is None:
            return

        if et == "2":
            oldPrice = data.get("lastPrice", -1e100)
            tdKey = "lastPriceTickDirection"
            if price > oldPrice:
                data[tdKey] = 1
            elif price == oldPrice:
                data[tdKey] = 0
            else:
                data[tdKey] = -1
            data["lastPrice"] = price
            data["lastSize"] = size

        else:
            priceLevel = msg["MDPriceLevel"]

            if priceLevel != 1:
                return

            if et == "0":
                oldPrice = data.get("lastPrice", -1e100)
                tdKey = "bidPriceTickDirection"
                if price > oldPrice:
                    data[tdKey] = 1
                elif price == oldPrice:
                    data[tdKey] = 0
                else:
                    data[tdKey] = -1
                data["bidPrice"] = price
                data["bidSize"] = size


            elif et == "1":
                oldPrice = data.get("lastPrice", -1e100)
                tdKey = "askPriceTickDirection"
                if price > oldPrice:
                    data[tdKey] = 1
                elif price == oldPrice:
                    data[tdKey] = 0
                else:
                    data[tdKey] = -1
                data["askPrice"] = price
                data["askSize"] = size
                
        for i, _ in enumerate(self._rows):
            if insKey == self._rows[i]:
                row = i
                self.dataChanged.emit(self.createIndex(row, 0),
                              self.createIndex(row, self.columnCount()))


class LineEdit(QLineEdit):

    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.completer = QCompleter(g.insModel.getInstrumentsName())
        self.completer.setModelSorting(QCompleter.CaseInsensitivelySortedModel)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setWrapAround(True)

        self.setCompleter(self.completer)


class Delegate(QStyledItemDelegate):

    def __init__(self, parent=None):
        super(Delegate, self).__init__(parent)
        print("create delegate")


    def createEditor(self, parent, option, index):
        # row = index.row()
        self.lineEdit = LineEdit(parent)
        # self.lineEdit.setStyleSheet("QLineEdit { background-color: rgba(1, 0, 0, 1); }")
        # self.lineEdit = QLineEdit(parent)
        # self.lineEdit.editingFinished.connect(self.commitAndCloseEditor)
        return self.lineEdit


    def setEditorData(self, widget, index):
        text = g.quoteModel.data(index, Qt.DisplayRole)
        if not text.isNull():
            widget.setText(text.value())


    def setModelData(self, editor, model, index):
        # print("setModelData", index.row(), index.column(), editor.text())
        name = editor.text()
        row = index.row()
        # g.quoteModel.setInstrument(row, name)
        instrument = g.insModel.getInstrument(name)
        exist = None
        if instrument:
            exist = instrument.get("ZMInstrumentID")

        if exist:
            g.subscriber.subscribe(instrument)
            model.addInsToRow(row, name, instrument)


    # def paint(self, painter, option, index):
    #     # background = index.data(Qt.BackgroundRole)
    #     row = index.row()
    #     color = QColor("#C8A355")
    #     background = QBrush(color)
    #     if row % 2 == 0:
    #         background = QBrush(QColor.darker(color, 120)) 
    #     
    #     painter.fillRect(option.rect, background)
    #     # painter.setPen(QPen(option.palette.foreground(), 0));
    #     painter.setBrush((index.data(Qt.ForegroundRole)));
    #     # painter.setBrush(option.palette.highlightedText());


class Dialog(QDialog):

    def __init__(self, parent):
        super().__init__(parent)

        self.initUI()
        self.setModal(True)
        self.accepted.connect(self._accepted)
        self.rejected.connect(self._rejected)


    def initUI(self):
        self.label = QLabel("Select columns")

        self.mainLayout = QVBoxLayout(self)
        self.mainLayout.addWidget(self.label)
        self.mainLayout.addWidget(self.createCheckbox())
        self.mainLayout.addWidget(self.createButtonBox())


    def createButtonBox(self):
        buttonBox = QDialogButtonBox(self)
        buttonBox.setEnabled(True)
        buttonBox.setOrientation(Qt.Horizontal)
        buttonBox.setStandardButtons(QDialogButtonBox.Ok |
           QDialogButtonBox.Cancel)

        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

        return buttonBox


    def createCheckbox(self):
        groupBox = QGroupBox()
        vbox = QVBoxLayout()
        self._checkBoxes = {}

        for k, v in COLUMN_NAME.items():
            cb = QCheckBox(v, self)
            self._checkBoxes[k] = cb
            if k == "instrument":
                cb.setEnabled(False)
                cb.setChecked(True)
            if k in g.quoteModel.getColumns():
                cb.setChecked(True)
            vbox.addWidget(cb)

        groupBox.setLayout(vbox)
        
        return groupBox

    def _accepted(self):
        # self.checked = []

        # for k, v in self._checkBoxes.items():
        #     if v.isChecked():
        #         self.checked.append(k)
        checked = [k for k, v in self._checkBoxes.items() if v.isChecked()]
        g.quoteModel.updateColumns(checked)
        g.quoteMonitor.initColumnSizes()


    def _rejected(self):
        print("rejected")


class TableStyle(QProxyStyle):

    def drawPrimitive(self, element, option, paintery, widget=None):
        if element == self.PE_IndicatorItemViewItemDrop and not option.rect.isNull():
            optionNew = QStyleOption(option)
            optionNew.rect.setLeft(0)
            # optionNew.rect.setTop(0)
            if widget:
                optionNew.rect.setRight(widget.width())
            option = optionNew
        paintery.setPen(QColor("#262525"))
        super().drawPrimitive(element, option, paintery, widget)


class QuoteMonitor(QMainWindow):

    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        
        self.rowHeight = 30
        # self.colInsWidth = 200
        # self.colWidth = 100
        
        sshFile = "style.qss"
        # sshFile = "material.qss"
        with open(sshFile, "r") as f:
            self.setStyleSheet(f.read())

        self._defaultColWidths = {
            "instrument": 200
        }
        self._defaultColWidthOther = 100
        self.initUI()
        
        if g.state:
            print("set column width from state")
            columnsWidth = g.state["table"]["columnsWidth"]
            geometry = g.state["geometry"]

            left = geometry["left"]
            top = geometry["top"]
            width = geometry["width"]
            height = geometry["height"]

            self.setGeometry(left, top, width, height)
            
            for i, v in enumerate(columnsWidth):
                self.table.setColumnWidth(i, v)


    def initUI(self):

        self.table = QTableView()
        self.delegate = Delegate()
        if g.state: 
            cols = g.state["table"]["columns"]
            for i, v in enumerate(cols):
                if v == "instrument":
                    g.colEditable = i
                    self.table.setItemDelegateForColumn(i, self.delegate)
                    break
        # self.table.verticalHeader().setSectionsMovable(True)
        self.table.horizontalHeader().setSectionsMovable(True)
        # self.table.horizontalHeader().sectionResized.connect(
        #         lambda a, b, c: self.resizeColumns(self.size(), self.size()))
        # self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setDragEnabled(True)
        self.table.setSelectionBehavior(self.table.SelectRows)
        self.table.setSelectionMode(self.table.SingleSelection)
        self.table.setDragDropMode(self.table.InternalMove)
        self.table.setDragDropOverwriteMode(False)
        self.table.setDropIndicatorShown(True)
        self.table.setAcceptDrops(True)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setStyle(TableStyle())
        self.table.setMouseTracking(True)

        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.showContextMenu)

        self.table.setModel(g.quoteModel)
         
        if not g.state:
            print("set column width from not state")
            accumWidth = 0
            for i in range(g.quoteModel.columnCount()):
                colName = g.quoteModel.columnName(i)
                colWidth = self._defaultColWidths.get(
                        colName, self._defaultColWidthOther)
                accumWidth += colWidth

                self.table.setColumnWidth(i, colWidth)

            self.resize(accumWidth + 20, 500)
    
        
        self.setCentralWidget(self.table)

        self.menubar = QMenuBar()

        self.fileMenu = self.menubar.addMenu("File")

        action = QAction("Preferences", self)
        self.fileMenu.addAction(action)
        self.fileMenu.triggered.connect(self.processtrigger)
        
        # menubar.setGeometry(300, 300, 300, 200)

        # mainLayout = QHBoxLayout()
        # mainLayout.addWidget(view)

        # self.setLayout(mainLayout)
        # self.setWindowTitle("Quote Monitor")


    # def showEvent(self, ev):
    #     self.appendedRowsIfNeeded()
    #     # self.setWidgetWidth()
    #     self.initColumnSizes()

    def showContextMenu(self, pos):
        self.contextMenu = QMenu(self)
        action = QAction("remove", self)
        action.triggered.connect(self.removeRow)
        self.contextMenu.addAction(action)
        self.contextMenu.exec(self.mapToGlobal(pos))


    def removeRow(self):
        item = self.table.currentIndex()
        row = item.row()
        g.quoteModel.removeRow(row)


    def processtrigger(self):
        self.dialog = Dialog(self)
        self.dialog.show()


    def appendedRowsIfNeeded(self):
        # L.debug("appended row if neened")
        self.height = QMainWindow.height(self)
        visibleRows = self.height / self.rowHeight
        rowsToAdd = ceil(visibleRows - g.quoteModel.rowCount())
        rowsToAdd = max(rowsToAdd, 0)

        for _ in range(rowsToAdd):
            g.quoteModel.appendRow()


    def initColumnSizes(self):
        numCols = g.quoteModel.columnCount()
        colWidth = round(self.width() / numCols)
        accumWidth = 0
        for i in range(numCols - 1):
            accumWidth += colWidth
            self.table.setColumnWidth(i, colWidth)
        self.table.setColumnWidth(numCols - 1, self.width() - accumWidth)


    # def resizeColumns(self, size, oldSize):
    #     numCols = g.quoteModel.columnCount()
    #     ratio = size.width() / oldSize.width()
    #     accumWidth = 0
    #     for i in range(numCols - 1):
    #         widthNow = round(self.table.columnWidth(i) * ratio)
    #         accumWidth += widthNow
    #         self.table.setColumnWidth(i, widthNow)
    #     self.table.setColumnWidth(numCols - 1, self.width() - accumWidth)


    def resizeEvent(self, ev):
        self.appendedRowsIfNeeded()
        # self.resizeColumns(ev.size(), ev.oldSize())


    def keyPressEvent(self, ev):
        if ev.key() == Qt.Key_Backspace:
            self.removeRow()


    def closeEvent(self, ev):
        self.saveApplicationState()
        writeToJSONFile(g.stateFile, g.state)

    
    # def sortIndicatorChanged(self, column=None, sortOrder=None):
    #     print("sortIndicatorChanged: column {}, sortOrder {}".format(column,
    #         sortOrder))
       

    def saveApplicationState(self):
        geom = self.geometry()
        columnsWidth = []
        header = []

        # for i in range(g.quoteModel.columnCount()):
        # print(g.quoteModel.headerData(i, Qt.Horizontal, Qt.DisplayRole))

        for i in range(g.quoteModel.columnCount()):
            idx = self.table.horizontalHeader().logicalIndex(i)
            header.insert(i, g.quoteModel.columnName(idx))
            width = self.table.columnWidth(idx)
            columnsWidth.insert(i, width)

        state = {}
        state["table"] = table = {}
        state["geometry"] = geometry = {}

        table["rows"] = g.quoteModel.getRows()
        table["columns"] = header
        table["data"] = {str(k): {"instrument": v["instrument"]}
                         for k, v in g.quoteModel._data.items() if k}
        table["columnsWidth"] = columnsWidth

        geometry["left"] = geom.left()
        geometry["top"] = geom.top()
        geometry["width"] = geom.width()
        geometry["height"] = geom.height()

        g.state = state


def loadApplicationState(sys):
    # print("load state", sys.stdin.read())
    if not os.isatty(sys.stdin.fileno()): 
        data = sys.stdin.read()
        g.state = json.loads(data)
        sys.stdin = open('/dev/tty')


def initSocket(ctlAddr, pubAddr):
    g.sockDeal = g.zctx.socket(zmq.DEALER)
    g.sockDeal.connect(ctlAddr)

    g.sockSub = g.zctx.socket(zmq.SUB)
    g.sockSub.connect(pubAddr)
    g.sockSub.subscribe("")


async def pubListener():
    L.info("publistener running")
    while True:
        parts = await g.sockSub.recv_multipart()
        topic = parts[0]
        spl = topic.split(b"\x00")
        msgType = spl[0].decode()
        endpoint = spl[1].decode()
        res = json.loads(parts[1].decode())

        g.subscriber.marketDataReceived(msgType, endpoint, res)


def setup_logging():
    fmt = "%(asctime)s.%(msecs)03d [%(name)s] [%(levelname)s] %(message)s"
    utils.logging.setup_root_logger(logging.DEBUG, fmt=fmt)
    utils.logging.disable_logger("quamash")
    utils.logging.disable_logger("parso")


def main():
    setup_logging()
    
    loadApplicationState(sys)

    g.app = QApplication(sys.argv)
    g.loop = QEventLoop(g.app)
    asyncio.set_event_loop(g.loop)

    ctlAddr = sys.argv[1]
    pubAddr = sys.argv[2]

    setup_interrupt_handling()

    g.zctx = zmq.asyncio.Context()
    initSocket(ctlAddr, pubAddr)
    
    g.insModel = InstrumentsModel()

    g.quoteModel = QuoteModel()
    
    g.subscriber = Subscriber(g.sockDeal, g.quoteModel)

    
    quotemon =  QuoteMonitor()
    g.quoteMonitor = quotemon

    quotemon.show()

    g.quoteModel.restoredSubscription()

    create_task(pubListener())

    exitCode = g.loop.run_forever()

    g.zctx.destroy(linger=0)

    sys.exit(exitCode)

if __name__ == "__main__":
    main()
    
