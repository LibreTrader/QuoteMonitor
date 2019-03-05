import signal
import json

from pprint import pprint

from PyQt5.QtCore import (QObject, pyqtProperty, pyqtSignal, pyqtSlot,
                          QFileInfo, QStandardPaths, QDir, QFileInfo, QTimer,
                          QLockFile)
from PyQt5.QtGui import QGuiApplication

# adapted from: https://stackoverflow.com/a/48432653/1793556

class Property(pyqtProperty):

    def __init__(self, value, name='', type_=None, notify=None):
        if type_ and notify:
            super().__init__(type_, self.getter, self.setter, notify=notify)
        self.value = value
        self.name = name
        if name:
            self.signalName = "on" + name[0].upper() + name[1:] + "Changed"


    def getter(self, inst=None):
        return self.value


    def setter(self, inst=None, value=None):
        self.value = value
        getattr(inst, self.signalName).emit()


class PropertyMeta(type(QObject)):

    def __new__(mcs, name, bases, attrs):
        for key in list(attrs.keys()):
            attr = attrs[key]
            if not isinstance(attr, Property):
                continue
            value = attr.value
            notifier = pyqtSignal()
            attrs[key] = prop = Property(
                value, key, type(value), notify=notifier)
            attrs[prop.signalName] = notifier
        return super().__new__(mcs, name, bases, attrs)


def getConfDir():
    genConfDir = QStandardPaths.writableLocation(
            QStandardPaths.GenericConfigLocation)
    confDir = genConfDir + QDir.separator() + "libretrader" 

    return confDir


def getLockfileName(path):
    fi = QFileInfo(path)
    return fi.path() + QDir.separator() + ".#" + fi.fileName()


def loadFromFile(file):
    lockfile = QLockFile(getLockfileName(file))
    lockfile.lock()

    if not QFileInfo(file).exists():
        return

    with open(file) as f:
        data = json.load(f)

    return data


def getFilePath(fileName):
    return getConfDir() + QDir.separator() + fileName


def writeToJSONFile(fileName, data):
    pprint(data)
    filePath = getFilePath(fileName)
    lockfile = QLockFile(getLockfileName(fileName))
    lockfile.lock()

    with open(filePath, 'w') as f:
        json.dump(data, f)

    lockfile.unlock()


# Call this function in your main after creating the QApplication
def setup_interrupt_handling(handler=None):
    """Setup handling of KeyboardInterrupt (Ctrl-C) for PyQt."""
    signal.signal(signal.SIGINT,
                  handler if handler else _default_interrupt_handler)
    # Regularly run some (any) python code, so the signal handler gets a
    # chance to be executed:
    safe_timer(50, lambda: None)


# Define this as a global function to make sure it is not garbage
# collected when going out of scope:
def _default_interrupt_handler(signum, frame):
    """Handle KeyboardInterrupt: quit application."""
    QGuiApplication.exit(130)


def safe_timer(timeout, func, *args, **kwargs):
    """
    Create a timer that is safe against garbage collection and overlapping
    calls. See: http://ralsina.me/weblog/posts/BB974.html
    """
    def timer_event():
        try:
            func(*args, **kwargs)
        finally:
            QTimer.singleShot(timeout, timer_event)
    QTimer.singleShot(timeout, timer_event)
