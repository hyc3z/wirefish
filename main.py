from PyQt5.QtGui import QFont
from scapy.all import *
from PyQt5.QtWidgets import QApplication, QMainWindow, QDialog, QTableWidgetItem, QFrame, QTableWidget, \
    QAbstractItemView
from PyQt5.QtCore import QThread, pyqtSignal, QCoreApplication
from PyQt5 import QtWidgets,QtCore,QtGui
from start_page import Ui_MainWindow
from capture_ui import Ui_Dialog
from utils.modifiedTableWidget import Table
import platform


def expand(packet):
    x = packet
    yield x.name, x.fields
    while x.payload:
        x = x.payload
        yield x.name, x.fields


def packet_to_layerlist(packet):
    return list(expand(packet))


class parentWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.main_ui = Ui_MainWindow()
        self.main_ui.setupUi(self)
        self.setWindowTitle(" ")
        self.showInterfaces()
        self.setMouseTracking(True)

    def showInterfaces(self):
        self.InterfaceThread = GetInterfaceThread(self.main_ui.tableWidget)
        self.InterfaceThread.AddInterface.connect(self.addInterface)
        self.initTable()
        self.InterfaceThread.start()
        self.main_ui.tableWidget.itemClicked.connect(self.interfaceSelected)

    def addInterface(self,res):
        self.main_ui.tableWidget.setRowCount(len(res))
        rowcount = 0
        for i in res:
            if isinstance(i, str):
                item = QtWidgets.QTableWidgetItem(i)
                item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                self.main_ui.tableWidget.setItem(rowcount, 1, item)
            else:
                for j in range(len(i)):
                    item = QtWidgets.QTableWidgetItem(i[j])
                    item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                    self.main_ui.tableWidget.setItem(rowcount, j, item)
            rowcount += 1

    def initTable(self):
        labels = ['index','iface','ip','mac']
        column_count = len(labels)
        self.main_ui.tableWidget.setColumnCount(column_count)
        for i in range(column_count):
            self.main_ui.tableWidget.horizontalHeader().setSectionResizeMode(i, QtWidgets.QHeaderView.ResizeToContents)


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
        self.capture_ui.setupUi(self)
        self.parentWindow = None
        self.capture_ui.pushButton.setText("Start")
        self.capture_ui.comboBox.addItem('Any')
        self.capture_ui.comboBox_2.addItem('Any')
        self.capture_ui.comboBox_3.addItem('Any')
        self.capture_ui.comboBox.currentIndexChanged.connect(self.filter_changed)
        self.capture_ui.comboBox_2.currentIndexChanged.connect(self.filter_changed)
        self.capture_ui.comboBox_3.currentIndexChanged.connect(self.filter_changed)
        self.capture_ui.pushButton.clicked.connect(self.start_capture)
        self.initTable()
        self.capture_ui.tableWidget.itemSelectionChanged.connect(self.show_info)
        self.index = 0
        self.setMouseTracking(True)


    def closeEvent(self,event):
        if self.parentWindow is not None:
            self.parentWindow.show()
        event.accept()

    def set_parent_window(self, parent):
        self.parentWindow = parent

    def showEvent(self, event):
        if self.sender is not None:
            rowc = self.sender().currentItem().row()
            self.interface_name = self.sender().item(rowc,1).text()
            self.setWindowTitle(self.interface_name + " " + self.sender().item(rowc,2).text())
            self.clearTab()
            self.index = 0
            self.srcset = set()
            self.dstset = set()
            self.protocolset = set()
            self.capture_ui.comboBox.clear()
            self.capture_ui.comboBox_2.clear()
            self.capture_ui.comboBox_3.clear()
            self.capture_ui.comboBox.addItem('Any')
            self.capture_ui.comboBox_2.addItem('Any')
            self.capture_ui.comboBox_3.addItem('Any')
            self.clearTable()
        event.accept()

    def initTable(self):
        labels = ['index','time','src','dst','protocol']
        column_count = len(labels)
        self.capture_ui.tableWidget.setColumnCount(column_count)
        self.capture_ui.tableWidget.setHorizontalHeaderLabels(labels)
        for i in range(column_count):
            self.capture_ui.tableWidget.horizontalHeader().setSectionResizeMode(i, QtWidgets.QHeaderView.ResizeToContents)

    def addPacket(self,packet_infolist):
        self.index += 1
        packet_infolist[0] = self.index
        self.packet_dict[self.index] = packet_infolist
        if packet_infolist[2] not in self.srcset:
            self.srcset.add(packet_infolist[2])
            self.capture_ui.comboBox.addItem(packet_infolist[2])
        if packet_infolist[3] not in self.dstset:
            self.dstset.add(packet_infolist[3])
            self.capture_ui.comboBox_2.addItem(packet_infolist[3])
        if packet_infolist[4] not in self.protocolset:
            self.protocolset.add(packet_infolist[4])
            self.capture_ui.comboBox_3.addItem(packet_infolist[4])
        if self.checksrc(packet_infolist) and self.checkdst(packet_infolist) and self.checkprotocol(packet_infolist):
            row = self.capture_ui.tableWidget.rowCount()
            self.capture_ui.tableWidget.setRowCount(row + 1)
            for i in range(5):
                item = QtWidgets.QTableWidgetItem(str(packet_infolist[i]))
                item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)

                self.capture_ui.tableWidget.setItem(row, i, item)
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
        self.capthread = ProcessingThread(self.interface_name)
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
        self.clearTable()
        for packet_infolist in self.packet_dict.values():
            if self.checksrc(packet_infolist) and self.checkdst(packet_infolist) and self.checkprotocol(packet_infolist):
                row = self.capture_ui.tableWidget.rowCount()
                self.capture_ui.tableWidget.setRowCount(row + 1)
                for i in range(5):
                    item = QtWidgets.QTableWidgetItem(str(packet_infolist[i]))
                    item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                    self.capture_ui.tableWidget.setItem(row, i, item)
                self.capture_ui.tableWidget.scrollToBottom()

    def CreateNewTab(self, tab, title, content):
        a = QtWidgets.QTextBrowser()
        a.setFrameStyle(QFrame.NoFrame)
        a.setText(content)
        a.setFont(QFont('Consolas', 10, QFont.Light))
        tab.addTab(a, title)

    def clearTable(self):
        self.capture_ui.tableWidget.clearContents()
        self.capture_ui.tableWidget.setRowCount(0)

    def clearTab(self):
        self.capture_ui.tabWidget.clear()

    def show_info(self):
        if self.sender is not None:
            self.clearTab()
            rowc = self.sender().currentItem().row()
            packet = self.packet_dict[int(self.sender().item(rowc,0).text())]
            data = packet_to_layerlist(packet[5])
            hexdata = hexdump(packet[5],True)
            self.CreateNewTab(self.capture_ui.tabWidget,"hex",hexdata)
            for i in data:
                str1 = ""
                for key in i[1]:
                    str1 += str(key)
                    str1 += " : "
                    str1 += str(i[1][key])
                    str1 += '\n'
                self.CreateNewTab(self.capture_ui.tabWidget,i[0],str1)


class GetInterfaceThread(QThread):

    AddInterface = pyqtSignal(list)

    def __init__(self, table, parent=None):
        QThread.__init__(self, parent=parent)
        self.table = table

    def get_interfaces(self):
        res = []
        if platform.system() == "Windows":
            data = IFACES.data
            for iface_name in sorted(data):
                dev = data[iface_name]
                mac = dev.mac
                mac = conf.manufdb._resolve_MAC(mac)
                res.append((str(dev.win_index), str(dev.name), str(dev.ip), mac))

        elif platform.system() == "Linux":
            res = get_if_list()

        return res


    def run(self):
        if self.isRunning:
            try:
                res = self.get_interfaces()
                self.AddInterface.emit(res)
            except Exception as e:
                print(e)
                self.stop()

    def stop(self):
        self.isRunning = False
        self.quit()
        self.terminate()



class ProcessingThread(QThread):

    AddPacket = pyqtSignal(list)
    Scroll = pyqtSignal(str)
    StartErr = pyqtSignal(Exception)

    def __init__(self, interface, parent=None):
        QThread.__init__(self, parent=parent)
        self.iface = interface
        self.count = 0

    def setIface(self,iface):
        self.iface = iface

    def checkproto(self,protoint):
        if protoint == 1: return "ICMP"
        elif protoint == 2: return "IGMP"
        elif protoint == 3: return "GGP"
        elif protoint == 6: return "TCP"
        elif protoint == 9: return "IGP"
        elif protoint == 17: return "UDP"
        elif protoint == 41: return "IPv6"
        elif protoint == 58: return "ICMPv6"
        else: return "Unknown ("+str(protoint)+")"

    def get_packet(self, pkt):
        self.count += 1
        packet_info = packet_to_layerlist(pkt)
        cur_time = time.asctime()
        protocol = packet_info[1][0]
        if protocol == "IP":
            base_protocol = self.checkproto(packet_info[1][1]['proto'])
            src = packet_info[1][1]['src']
            dst = packet_info[1][1]['dst']
        elif protocol == "ARP":
            base_protocol = protocol
            src = packet_info[1][1]['psrc']
            dst = packet_info[1][1]['pdst']
        elif protocol == "IPv6":
            base_protocol = protocol
            src = packet_info[1][1]['src']
            dst = packet_info[1][1]['dst']
        else:
            base_protocol = protocol
            src = packet_info[0][1]['src']
            dst = packet_info[0][1]['dst']
        self.AddPacket.emit([self.count, cur_time, src, dst, base_protocol, pkt])

    def run(self):
        while self.isRunning:
            try:
                sniff(prn=self.get_packet, iface=self.iface, count=0)
            except Exception as e:
                print(e)
                self.StartErr.emit(e)
                self.stop()


    def stop(self):
        self.isRunning = False
        self.quit()
        self.terminate()


def main():
    app = QApplication(sys.argv)
    QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
    window = parentWindow()
    child = childWindow()
    child.set_parent_window(window)
    window.main_ui.tableWidget.itemClicked.connect(child.show)
    window.show()
    sys.exit(app.exec_())


if __name__=='__main__':
    main()


