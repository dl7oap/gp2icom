#!/usr/bin/env python3

'''
Author  : Andreas Puschendorf, DL7OAP
Version : 001
Date    : 2020-09-01

This script is plugged between gpredict and ic9700 based on python 3.7
It is listing on port 4532 for gpredict frequencies
and it is sending frequencies and startsequences for ic9700 with icom CAT CIV commands to the serial port.

Usage:
1) select a satellite
2) start the loop
3) start gpredit tracking

'''



from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

import traceback
import socket
import sys
import icom

class Satellite:
    name = ""
    mode = ""  # SSB, FM, CW
    satmode = ""  # U/V, V/U, S/U, U/U, V/V
    rit = 0


class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)


class Worker(QRunnable):
    '''
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    '''

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()

        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

        # Add the callback to our kwargs
        self.kwargs['progress_callback'] = self.signals.progress

    @pyqtSlot()
    def run(self):
        '''
        Initialise the runner function with passed args, kwargs.
        '''

        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done


class MainWindow(QMainWindow):

    HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
    PORT_SERVER = 4532  # Port to listen on (non-privileged ports are > 1023)
    FREQUENCY_OFFSET_UPLINK = 40  # needed Uplinkfrequency shift in Hz before a correction is send to transceiver
    FREQUENCY_OFFSET_DOWNLINK = 25  # needed Downlinkfrequency shift in Hz before a correction is send to transceiver

    rit = 0         #  rit to use
    last_rit = 0    #  last rit which was set

    isSatelliteDuplex = True
    isDownlinkConstant = False

    satellites = []

    #  ####################################################

    def setStartSequenceSSB(self, usb=False):

        # define uplink
        ic9700.setVFO('Main')
        ic9700.setVFO('VFOA')
        ic9700.setRitFrequence(0)
        ic9700.setRitOn(False)

        if usb:
            ic9700.setMode('USB')
        else:
            ic9700.setMode('LSB')
        ic9700.setSplitOn(False)

        # define downlink
        ic9700.setVFO('SUB')
        ic9700.setVFO('VFOA')
        if usb:
            ic9700.setMode('LSB')
        else:
            ic9700.setMode('USB')

    def setStartSequenceCW(self, usb=False):

        # define uplink
        ic9700.setVFO('Main')
        ic9700.setVFO('VFOA')
        ic9700.setRitFrequence(0)
        ic9700.setRitOn(False)

        if usb:
            ic9700.setMode('CW')
        else:
            ic9700.setMode('CW')
        ic9700.setSplitOn(False)

        # define downlink
        ic9700.setVFO('SUB')
        ic9700.setVFO('VFOA')
        if usb:
            ic9700.setMode('LSB')
        else:
            ic9700.setMode('USB')

    def setStartSequenceFM(self):

        # define uplink
        ic9700.setVFO('MAIN')
        ic9700.setVFO('VFOA')
        ic9700.setMode('FM')
        ic9700.setSplitOn(False)
        ic9700.setAfcOn(False)
        ic9700.setRitFrequence(0)
        ic9700.setRitOn(False)
        ic9700.setToneHz('670')
        ic9700.setToneOn(True)

        # define downlink
        ic9700.setVFO('SUB')
        ic9700.setVFO('VFOA')
        ic9700.setMode('FM')
        ic9700.setToneOn(False)
        ic9700.setAfcOn(True)
        ic9700.setRitFrequence(0)
        ic9700.setRitOn(False)

    def setStartSequenceSimplex(self):

        # define uplink
        ic9700.setVFO('MAIN')
        ic9700.setVFO('VFOB')
        ic9700.setMode('FM')
        ic9700.setToneOn(False)
        ic9700.setAfcOn(False)
        ic9700.setRitFrequence(0)
        ic9700.setRitOn(False)

        # define downlink
        ic9700.setVFO('VFOA')
        ic9700.setMode('FM')
        ic9700.setToneOn(False)
        ic9700.setSplitOn(True)
        ic9700.setAfcOn(True)
        ic9700.setRitFrequence(0)
        ic9700.setRitOn(False)

    def setUplink(self, up):

        # set uplink frequency
        ic9700.setVFO('MAIN')
        ic9700.setFrequence(up)
        ic9700.setVFO('SUB')

    def setDownlink(self, dw):

        # set uplink frequency
        # ic9700.setVFO('SUB')   # if user did not activate sub manually, we can speed up here
        ic9700.setFrequence(dw)

    def setUplinkSimplex(self, up):

        # only update of frequencies if PTT off
        if ic9700.isPttOff():
            # set uplink frequency
            ic9700.setVFO('VFOB')
            ic9700.setFrequence(up)
            ic9700.setVFO('VFOA')

    def setDownlinkSimplex(self, dw):

        # only update of frequencies if PTT off
        if ic9700.isPttOff():
            # set downlink frequency
            ic9700.setVFO('VFOA')
            ic9700.setFrequence(dw)

    def getBandFromFrequency(self, frequency):
        band = '2M'
        if int(frequency) > 150000000:
            band = '70CM'
        if int(frequency) > 470000000:
            band = '23CM'
        return band

    def activateCorrectUplinkBandInMain(self, type_of_uplink_band):
        ic9700.setVFO('MAIN')
        main_frequency = ic9700.getFrequence()
        ic9700.setVFO('SUB')
        sub_frequency = ic9700.getFrequence()

        if type_of_uplink_band == MainWindow.getBandFromFrequency(self, main_frequency):  # is uplink band in main -> nothing to do
            return
        elif type_of_uplink_band == MainWindow.getBandFromFrequency(self, sub_frequency):  # is uplink band in sub -> switch bands
            ic9700.setExchange()
        else:  # is uplink band not in main and sub -> set band in main
            ic9700.setVFO('MAIN')
            if type_of_uplink_band == '23CM':
                ic9700.setFrequence('1295000000')
            if type_of_uplink_band == '70CM':
                ic9700.setFrequence('435000000')
            if type_of_uplink_band == '2M':
                ic9700.setFrequence('145900000')


    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        try:
            with open('satellites.txt', 'r') as fp:
                for line in fp:
                    new_satellite = Satellite()
                    new_satellite.name = line.split(",")[0] + " " + line.split(",")[1]
                    new_satellite.mode = line.split(",")[1]
                    new_satellite.rit = line.split(",")[2]
                    new_satellite.satmode = line.split(",")[3].replace("\n", "")
                    self.satellites.append(new_satellite)
        finally:
            fp.close()

        layout = QGridLayout()

        comboSatellite = QComboBox(self)
        for sat in self.satellites:
            comboSatellite.addItem(sat.name)
        comboSatellite.currentTextChanged.connect(self.on_combobox_changed)

        buttonDoLoop = QPushButton("Start loop")
        buttonDoLoop.pressed.connect(self.doLoop)

        buttonRitUp = QPushButton("RIT +25Hz")
        buttonRitUp.pressed.connect(self.setRitUp)

        buttonRitDown = QPushButton("RIT -25Hz")
        buttonRitDown.pressed.connect(self.setRitDown)

        self.ritEdit = QLineEdit(self)

        layout.addWidget(comboSatellite, 0, 0)
        layout.addWidget(buttonDoLoop, 0, 2)

        layout.addWidget(buttonRitUp, 1, 0)
        layout.addWidget(buttonRitDown, 1, 1)
        layout.addWidget(self.ritEdit, 1, 2)


        radiobutton = QRadioButton("Sat constant")
        radiobutton.setChecked(True)
        radiobutton.country = "Sat constant"
        radiobutton.setToolTip("Frequency on satellite transponder will be held constant")
        radiobutton.toggled.connect(self.onRadioButtonSatelliteConstantClicked)
        layout.addWidget(radiobutton, 4, 0)

        radiobutton = QRadioButton("Downlink constant")
        radiobutton.setChecked(False)
        radiobutton.country = "Downlink constant"
        radiobutton.setToolTip("Frequency on the downlink will be held constant")
        radiobutton.toggled.connect(self.onRadioButtonDownlinkConstantClicked)
        layout.addWidget(radiobutton, 4, 1)


        w = QWidget()
        w.setLayout(layout)

        self.setWindowTitle("gpredict and ic9700")
        self.setCentralWidget(w)
        self.show()

        self.threadpool = QThreadPool()
        print("Multithreading with maximum %d threads" % self.threadpool.maxThreadCount())

        self.timer = QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.recurring_timer)
        self.timer.start()

    def onRadioButtonDownlinkConstantClicked(self):
        self.isDownlinkConstant = True

    def onRadioButtonSatelliteConstantClicked(self):
        self.isDownlinkConstant = False

    def on_combobox_changed(self, value):
        for sat in self.satellites:
            if sat.name == value:

                ic9700.setSatelliteMode(False)

                # set correct bands in SUB and MAIN
                if sat.satmode == 'U/V':
                    self.activateCorrectUplinkBandInMain('70CM')
                    self.isSatelliteDuplex = True
                if sat.satmode == 'V/U':
                    self.activateCorrectUplinkBandInMain('2M')
                    self.isSatelliteDuplex = True
                if sat.satmode == 'S/U':
                    self.activateCorrectUplinkBandInMain('23CM')
                    self.isSatelliteDuplex = True
                if sat.satmode == 'V/V':
                    self.activateCorrectUplinkBandInMain('2M')
                    self.isSatelliteDuplex = False
                if sat.satmode == 'U/U':
                    self.activateCorrectUplinkBandInMain('70CM')
                    self.isSatelliteDuplex = False
                if sat.satmode == 'S/S':
                    self.activateCorrectUplinkBandInMain('23CM')
                    self.isSatelliteDuplex = False

                self.rit = int(sat.rit)

                # TODO: implement choice of USB and LSB Mode Uplink
                if self.isSatelliteDuplex:
                    if sat.mode == 'SSB':
                        ic9700.setDualWatch(True)
                        self.setStartSequenceSSB()
                        ic9700.setVFO('SUB')
                        ic9700.setRitOn(True)
                        ic9700.setRitFrequence(int(self.rit))
                    if sat.mode == 'CW':
                        ic9700.setDualWatch(True)
                        self.setStartSequenceCW()
                        ic9700.setVFO('SUB')
                        ic9700.setRitOn(True)
                        ic9700.setRitFrequence(int(self.rit))
                    if sat.mode == 'FM':
                        self.setStartSequenceFM()
                else:
                    self.setStartSequenceSimplex()

                break

    def execute_main_loop(self, progress_callback):
        uplink = '0'
        downlink = '0'
        last_uplink = '0'
        last_downlink = '0'

        ###############################################
        # start socket for gpredict
        ###############################################

        # start tcp server
        sock_gpredict = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock_gpredict.bind((self.HOST, self.PORT_SERVER))
        sock_gpredict.listen(1)

        ###############################################
        # main loop
        ###############################################

        while True:
            conn, addr = sock_gpredict.accept()
            print('Connected by', addr)
            while 1:
                data = conn.recv(1000)
                print('\n######   LOOP   START   ######')
                print('gpredict: ' + data.decode('utf-8').replace('\n', ''))
                print('icom:', ic9700.getWhatIcomWantsToSay())  # TODO: Way not to read the download but to be informed
                # changes, but get them directly from ICOM device if
                # the user is using the dial knob
                if not data:
                    break
                if self.rit != self.last_rit:
                    ic9700.setRitFrequence(self.rit)
                    self.last_rit = self.rit
                if data[0] in [70, 73]:  # I, F
                    # get downlink and uplink from gpredict
                    # and set downlink and uplink to icom
                    cut = data.decode('utf-8').split(' ')
                    if data[0] == 70:  # F - gpredict ask for downlink
                        if self.isDownlinkConstant:
                            downlink = last_downlink
                        else:
                            downlink = cut[len(cut) - 1].replace('\n', '')
                    if data[0] == 73:  # I - gpredict ask for uplink
                        uplink = cut[len(cut) - 1].replace('\n', '')
                    print('** gp2icom: last  ^ ' + last_uplink + ' v ' + last_downlink)
                    print('** gp2icom: fresh ^ ' + uplink + ' v ' + downlink)
                    # only if uplink or downlink changed > 0 10Hz Column, then update
                    if (abs(int(last_uplink) - int(uplink)) > self.FREQUENCY_OFFSET_UPLINK):
                        if self.isSatelliteDuplex:
                            MainWindow.setUplink(self, uplink)
                        else:
                            MainWindow.setUplinkSimplex(self, uplink)
                        last_uplink = uplink
                    if not self.isDownlinkConstant:
                        if (abs(int(last_downlink) - int(downlink)) > self.FREQUENCY_OFFSET_DOWNLINK):
                            if self.isSatelliteDuplex:
                                MainWindow.setDownlink(self, downlink)
                            else:
                                MainWindow.setDownlinkSimplex(self, downlink)
                            last_downlink = downlink
                    conn.send(b'RPRT 0')  # Return Data OK to gpredict
                elif data[0] in [102, 105]:  # i, f
                    # read downlink or uplink from icom
                    # and send it to gpredict
                    if not self.isSatelliteDuplex:
                        conn.send(b'RPRT')
                    else:
                        if data[0] == 102:  # f - gpredict ask for downlink
                            print('** gpredict ask for downlink ')
                            # ic9700.setVFO('SUB')
                            actual_sub_frequency = ic9700.getFrequence()  # TODO: das ist suboptimal für 1,2 GHz
                            if 1 == 1:  # TODO hier war die Prüfung, ob die Frequenz erfolgreich ausgelesen werden konnte!
                                downlink = actual_sub_frequency
                                last_downlink = actual_sub_frequency
                                print('** gp2icom: dial down: ' + actual_sub_frequency)
                                b = bytearray()
                                b.extend(map(ord, actual_sub_frequency + '\n'))
                                conn.send(b)
                        elif data[0] == 105:  # i - gpredict ask for uplink
                            # we do not look for dial on uplink,
                            # we just ignore it and send back the last uplink frequency
                            print('** gp2icom: last uplink : ' + uplink)
                            b = bytearray()
                            b.extend(map(ord, uplink + '\n'))
                            conn.send(b)
                elif data[0] == 116:  # t ptt
                    conn.send(b'0')
                else:
                    conn.send(b'RPRT 0')  # Return Data OK to gpredict
            print('connect closed')
            conn.close()

    def setRitUp(self):
        self.rit += 25

    def setRitDown(self):
        self.rit -= 25

    def print_output(self, s):
        print(s)

    def thread_complete(self):
        print("THREAD COMPLETE!")

    def doLoop(self):
        # Pass the function to execute
        worker = Worker(self.execute_main_loop)  # Any other args, kwargs are passed to the run function
        worker.signals.result.connect(self.print_output)
        worker.signals.finished.connect(self.thread_complete)

        # Execute
        self.threadpool.start(worker)

    def recurring_timer(self):
        self.ritEdit.setText(str(self.rit))


ic9700 = icom.ic9700('/dev/ic9700a', '19200')
app = QApplication([])
window = MainWindow()
app.exec_()
ic9700.close()
