import os

from PyQt5.QtCore import QPropertyAnimation
import time

from PyQt5.QtGui import QFont

from utils.var import VAR
from scapy.layers.inet import icmptypes

from utils import win_get_key
from netifaces import ifaddresses, AF_INET, AF_INET6
import start_page
import sys
from scapy.all import *
from PyQt5.QtWidgets import QApplication, QMainWindow, QDialog, QTableWidgetItem, QFrame
from PyQt5.QtCore import QThread,pyqtSignal
from PyQt5 import QtWidgets,QtCore,QtGui
from utils import packet_r
from ctypes import *
import netifaces
from start_page import Ui_MainWindow
from capture import Ui_Dialog
from utils.packet_r import igmptypes


class parentWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.main_ui = Ui_MainWindow()
        self.main_ui.setupUi(self)
        self.showInterfaces()


    def showInterfaces(self):

        self.data = IFACES.data
        res = []
        for iface_name in sorted(self.data):
            dev = self.data[iface_name]
            mac = dev.mac
            mac = conf.manufdb._resolve_MAC(mac)
            res.append((str(dev.win_index), str(dev.name), str(dev.ip), mac))
        # print(res)

        self.initTable()
        # interfaces = win_get_key.get_interfaces()
        self.main_ui.tableWidget.setRowCount(len(res))
        rowcount = 0
        for i in res:
            item0 = QtWidgets.QTableWidgetItem(i[0])
            item0.setFlags(
                QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.main_ui.tableWidget.setItem(rowcount, 0, item0)

            item1 = QtWidgets.QTableWidgetItem(i[1])
            item1.setFlags(
                QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.main_ui.tableWidget.setItem(rowcount, 1, item1)

            item2 = QtWidgets.QTableWidgetItem(i[2])
            item2.setFlags(
                QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.main_ui.tableWidget.setItem(rowcount, 2, item2)

            item3 = QtWidgets.QTableWidgetItem(i[3])
            item3.setFlags(
                QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.main_ui.tableWidget.setItem(rowcount, 3, item3)

            rowcount += 1
        self.main_ui.tableWidget.itemDoubleClicked.connect(self.interfaceSelected)

    def initTable(self):
        self.main_ui.tableWidget.setColumnCount(4)
        self.main_ui.tableWidget.setHorizontalHeaderLabels(['index','iface','ip','mac'])
        self.main_ui.tableWidget.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        self.main_ui.tableWidget.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        self.main_ui.tableWidget.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        self.main_ui.tableWidget.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        self.main_ui.tableWidget.horizontalHeader().setStretchLastSection(True)

    def interfaceSelected(self):
        self.hide()

class childWindow(QDialog):
    def __init__(self):
        QDialog.__init__(self)

        self.packet_dict = {}
        self.srcset = set()
        self.dstset = set()
        self.protocolset = set()
        self.capture_ui=Ui_Dialog()
        self.share = VAR()
        self.capture_ui.setupUi(self)
        self.parentWindow = None
        self.capture_ui.pushButton.setText("Start")
        self.capture_ui.comboBox_2.addItem('Any')
        self.capture_ui.comboBox.addItem('Any')
        self.capture_ui.comboBox_3.addItem('Any')
        self.capture_ui.comboBox.currentIndexChanged.connect(self.filter_changed)
        self.capture_ui.comboBox_2.currentIndexChanged.connect(self.filter_changed)
        self.capture_ui.comboBox_3.currentIndexChanged.connect(self.filter_changed)

        self.capture_ui.pushButton.clicked.connect(self.start_capture)
        self.initTable()
        self.capture_ui.tableWidget.itemDoubleClicked.connect(self.show_info)



    def closeEvent(self,event):
        if self.parentWindow is not None:
            self.parentWindow.show()
        event.accept()

    def set_parent_window(self, parent):
        self.parentWindow = parent

    def showEvent(self, event):
        if self.sender is not None:
            rowc = self.sender().currentItem().row()
            self.setWindowTitle(self.sender().item(rowc,1).text())
            self.clearTable()
            self.clearTab()
        event.accept()

    def initTable(self):
        self.capture_ui.tableWidget.setColumnCount(5)
        self.capture_ui.tableWidget.setHorizontalHeaderLabels(['index','time','src','dst','protocol'])
        self.capture_ui.tableWidget.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        self.capture_ui.tableWidget.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        self.capture_ui.tableWidget.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        self.capture_ui.tableWidget.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        self.capture_ui.tableWidget.horizontalHeader().setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)

        self.capture_ui.tableWidget.horizontalHeader().setStretchLastSection(True)


    # 获取包信息



    def addPacket(self,packet_infolist):
        self.packet_dict[packet_infolist[0]] = packet_infolist
        len_pre = len(self.srcset)
        self.srcset.add(packet_infolist[2])
        if len(self.srcset) - len_pre:
            self.capture_ui.comboBox.addItem(packet_infolist[2])

        len_pre = len(self.dstset)
        self.dstset.add(packet_infolist[3])
        if len(self.dstset) - len_pre:
            self.capture_ui.comboBox_2.addItem(packet_infolist[3])

        len_pre = len(self.protocolset)
        self.protocolset.add(packet_infolist[4])
        if len(self.protocolset) - len_pre:
            self.capture_ui.comboBox_3.addItem(packet_infolist[4])

        if self.checksrc(packet_infolist) and self.checkdst(packet_infolist) and self.checkprotocol(packet_infolist):
            row = self.capture_ui.tableWidget.rowCount()
            self.capture_ui.tableWidget.setRowCount(row + 1)
            # count
            item0 = QtWidgets.QTableWidgetItem(str(packet_infolist[0]))
            self.capture_ui.tableWidget.setItem(row, 0, item0)
            item0.setFlags(
                QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            # time
            item1 = QtWidgets.QTableWidgetItem(str(packet_infolist[1]))
            self.capture_ui.tableWidget.setItem(row, 1, item1)
            item1.setFlags(
                QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            # src
            item2 = QtWidgets.QTableWidgetItem(str(packet_infolist[2]))
            self.capture_ui.tableWidget.setItem(row, 2, item2)
            item2.setFlags(
                QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            # dst
            item3 = QtWidgets.QTableWidgetItem(str(packet_infolist[3]))
            self.capture_ui.tableWidget.setItem(row, 3, item3)
            item3.setFlags(
                QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            # protocol
            item4 = QtWidgets.QTableWidgetItem(str(packet_infolist[4]))
            self.capture_ui.tableWidget.setItem(row, 4, item4)
            item4.setFlags(
                QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.capture_ui.tableWidget.scrollToBottom()


    def stop_capture(self):
        try:
            self.capthread.stop()
        except:
            pass
        self.capture_ui.pushButton.setText('Start')
        self.capture_ui.pushButton.clicked.disconnect(self.stop_capture)
        self.capture_ui.pushButton.clicked.connect(self.start_capture)

    def start_capture(self):
        self.capthread = ProcessingThread(self.windowTitle())
        self.capthread.AddPacket.connect(self.addPacket)
        self.capthread.StartErr.connect(self.resetbutton)
        self.capthread.start()
        self.capture_ui.pushButton.setText('Stop')
        self.capture_ui.pushButton.clicked.disconnect(self.start_capture)
        self.capture_ui.pushButton.clicked.connect(self.stop_capture)


    def resetbutton(self):
        self.capture_ui.pushButton.setText('Start')
        self.capture_ui.pushButton.clicked.disconnect(self.stop_capture)
        self.capture_ui.pushButton.clicked.connect(self.start_capture)

    def checksrc(self,packet):
        if self.capture_ui.comboBox.currentText() == 'Any':
            return True
        else:
            return self.capture_ui.comboBox.currentText() == packet[2]

    def checkdst(self,packet):
        if self.capture_ui.comboBox_2.currentText() == 'Any':
            return True
        else:
            return self.capture_ui.comboBox_2.currentText() == packet[3]

    def checkprotocol(self,packet):
        if self.capture_ui.comboBox_3.currentText() == 'Any':
            return True
        else:
            return self.capture_ui.comboBox_3.currentText() == packet[4]

    def filter_changed(self):
        self.capture_ui.tableWidget.clear()
        self.capture_ui.tableWidget.setRowCount(0)
        for packet_infolist in self.packet_dict.values():
            if self.checksrc(packet_infolist) and self.checkdst(packet_infolist) and self.checkprotocol(packet_infolist):
                row = self.capture_ui.tableWidget.rowCount()
                self.capture_ui.tableWidget.setRowCount(row + 1)
                # count
                item0 = QtWidgets.QTableWidgetItem(str(packet_infolist[0]))
                self.capture_ui.tableWidget.setItem(row, 0, item0)
                item0.setFlags(
                    QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                # time
                item1 = QtWidgets.QTableWidgetItem(str(packet_infolist[1]))
                self.capture_ui.tableWidget.setItem(row, 1, item1)
                item1.setFlags(
                    QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                # src
                item2 = QtWidgets.QTableWidgetItem(str(packet_infolist[2]))
                self.capture_ui.tableWidget.setItem(row, 2, item2)
                item2.setFlags(
                    QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                # dst
                item3 = QtWidgets.QTableWidgetItem(str(packet_infolist[3]))
                self.capture_ui.tableWidget.setItem(row, 3, item3)
                item3.setFlags(
                    QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                # protocol
                item4 = QtWidgets.QTableWidgetItem(str(packet_infolist[4]))
                self.capture_ui.tableWidget.setItem(row, 4, item4)
                item4.setFlags(
                    QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                self.capture_ui.tableWidget.scrollToBottom()

    def CreateNewTab(self, tab, title, content):

        a = QtWidgets.QTextBrowser()
        a.setFrameStyle(QFrame.NoFrame)
        a.setText(content)
        a.setFont(QFont('Consolas', 10, QFont.Light))
        tab.addTab(a, title)

    def clearTable(self):
        self.capture_ui.tableWidget.clear()
        self.capture_ui.tableWidget.setRowCount(0)

    def clearTab(self):
        self.capture_ui.tabWidget.clear()

    def show_info(self):
        if self.sender is not None:
            self.clearTab()
            rowc = self.sender().currentItem().row()
            packet = self.packet_dict[int(self.sender().item(rowc,0).text())]
            data = packet[5].packet_to_layerlist()
            hexdata = packet[5].packet_to_hexdump()

            self.CreateNewTab(self.capture_ui.tabWidget,"hex",hexdata)
            for i in data:
                str1 = ""
                for key in i[1]:
                    str1 += str(key)
                    str1 += " : "
                    str1 += str(i[1][key])
                    str1 += '\n'
                self.CreateNewTab(self.capture_ui.tabWidget,i[0],str1)


class ProcessingThread(QThread):

    AddPacket = pyqtSignal(list)
    Scroll = pyqtSignal(str)
    StartErr = pyqtSignal(Exception)

    def __init__(self, iface, parent=None):
        QThread.__init__(self, parent=parent)
        self.setIface(iface)
        self.isRunning = True
        self.count = 0

    def setIface(self,iface):
        self.iface = iface

    def showpkt(self, pkt):
        self.count += 1
        pkt = packet_r.Packet_r(pkt)
        packet_info = pkt.packet_to_layerlist()
        cur_time = time.asctime()
        src = packet_info[0][1]['src']
        dst = packet_info[0][1]['dst']
        protocol = packet_info[1][0]
        self.AddPacket.emit([self.count, cur_time, src, dst, protocol, pkt])

    def run(self):

        while self.isRunning:
            try:
                sniff(prn=self.showpkt, iface=self.iface, count=1)
            except Exception as e:
                print(e)
                self.StartErr.emit(e)
                self.stop()


    def stop(self):
        self.isRunning = False
        self.quit()
        self.terminate()
        self.wait()


def main():
    app = QApplication(sys.argv)
    window = parentWindow()
    child = childWindow()
    child.set_parent_window(window)
    # 通过toolButton将两个窗体关联
    window.main_ui.tableWidget.itemDoubleClicked.connect(child.show)
    window.show()
    # 显示
    sys.exit(app.exec_())


if __name__=='__main__':
    main()

