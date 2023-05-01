#!/usr/bin/env python3

"""
Author  : Andreas Puschendorf, DL7OAP
Version : 001
Date    : 2020-09-01

This script is plugged between gpredict and ic9700 or ic9100 based on python 3.7
It is listing on port 4532 for gpredict frequencies
and it is sending frequencies and startsequences for ic9700/ic9100 with icom CAT CIV commands to the serial port.

Usage:
1) select a satellite
2) start gpredit tracking

Modified: by Alex Krist, KR1ST
Date    : 11/2020
Comments: The original script has been adapted for use with the Icom IC-9100. The IC-9100 does
          not support CAT control for RIT like the IC-9700 does for which the script was originally
          developed. This script will, through the icom.py module, adjust
          the main and sub VFO frequency for the offset read from the satellites.txt file. By
          applying the frequency offset to the main and sub VFO's you will still be able to use
          the RIT on the radio when needed.
          This modified script also adds support for up to three Gqrx instances to act as
          panadapters, or to use as separate receivers. The frequencies that the Gqrx instances are
          tuned to are in sync with the radio main and sub VFO's. The Gqrx ports that this script
          will send frequency information to are defined by PORT_GQRX_VHF, PORT_GQRX_UHF, and
          PORT_GQRX_SHF.
          A little extra excepton information has been added. Most print statements have been
          removed or commented out to improve performance. It probably would have been better to
          add a debug option that would print relevant info, but I'm lazy. :)
          This modified script will easily allow for Gpredict frequency updates every 250ms.
          Gpredict and the Gqrx instances will track with with the radio if the frequency on the
          IC-9100 is changed using the main dial.
          I have tested this only on a Raspberry Pi 4B (4Gb version) with FM and linear satellites.

          Many thanks to Andreas, DL7OAP, for writing the original IC-9700 script and making it
          available to everyone. I am very grateful for his work as it provided me with a real
          solution to use Gpredict on a Raspberry Pi to apply doppler tracking to the IC-9100 and
          allowing to set a frequency offset per satellite.

"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

import traceback
import socket
import sys
import icom
import time
import linecache


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
        """
        Initialise the runner function with passed args, kwargs.
        """

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
    PORT_GQRX_VHF = 7300  # VHF gqrx port 
    PORT_GQRX_UHF = 7301  # UHF gqrx port 
    PORT_GQRX_SHF = 7302  # SHF gqrx port 
    FREQUENCY_OFFSET_UPLINK = 40  # needed Uplinkfrequency shift in Hz before a correction is send to transceiver
    FREQUENCY_OFFSET_DOWNLINK = 25  # needed Downlinkfrequency shift in Hz before a correction is send to transceiver

    rit = 0  # rit to use
    last_rit = 0  # last rit which was set

    isSatelliteDuplex = True
    isDownlinkConstant = False
    isLoopActive = True

    satellites = []

    #  ####################################################

    def activateCorrectUplinkBandInMain(self, up_band):
        freq = {'U': '433000000', 'V': '145900000', 'L': '1295000000'}
        icomTrx.setVFO('MAIN')
        icomTrx.setVFO('VFOA')
        if not icomTrx.setFrequence(freq.get(up_band)):
            icomTrx.setExchange()
            icomTrx.setFrequence(freq.get(up_band))

    def setStartSequenceSatellite(self, uplinkMode):

        # define uplink
        icomTrx.setVFO('Main')
        icomTrx.setVFO('VFOA')
        icomTrx.setMode(uplinkMode)
        icomTrx.setSplitOn(False)
        icomTrx.setRitOn(False)
        if uplinkMode == 'FM':
            icomTrx.setAfcOn(False)
            icomTrx.setToneHz('670')
            icomTrx.setToneOn(True)

        # define downlink
        icomTrx.setVFO('SUB')
        icomTrx.setVFO('VFOA')
        icomTrx.setRitOn(False)
        if uplinkMode == 'USB':
            icomTrx.setMode('LSB')
        else:
            icomTrx.setMode('USB')
        if uplinkMode == 'FM':
            icomTrx.setMode('FM')
            icomTrx.setToneOn(False)
            icomTrx.setAfcOn(False)  # you could set it to True, but gpredict is accurate, so you don't really need AFC

    def setStartSequenceSimplex(self, uplinkMode):

        # define uplink
        icomTrx.setVFO('MAIN')
        icomTrx.setVFO('VFOB')
        if uplinkMode == 'FM':
            icomTrx.setMode('FM')
        if uplinkMode == 'FM-D':
            icomTrx.setMode('FM-D')
        if uplinkMode == 'SSB-D':
            icomTrx.setMode('USB-D')
        icomTrx.setToneOn(False)
        icomTrx.setAfcOn(False)
        icomTrx.setRitFrequence(0)
        icomTrx.setRitOn(False)

        # define downlink
        icomTrx.setVFO('VFOA')
        if uplinkMode == 'FM':
            icomTrx.setMode('FM')
        if uplinkMode == 'FM-D':
            icomTrx.setMode('FM-D')
        if uplinkMode == 'SSB-D':
            icomTrx.setMode('USB-D')
        icomTrx.setToneOn(False)
        icomTrx.setSplitOn(True)
        icomTrx.setAfcOn(False)
        icomTrx.setRitFrequence(0)
        icomTrx.setRitOn(False)

    def setUplink(self, up):
        icomTrx.setVFO('MAIN')
        icomTrx.setFrequence(up)
        icomTrx.setVFO('SUB')

    def setDownlink(self, dw):
        icomTrx.setVFO('SUB')
        icomTrx.setFrequence(str(int(dw) + int(self.rit)))

    def setUplinkSimplex(self, up):
        if icomTrx.isPttOff():
            # icom 9700 can set the unselected VFO within the MAIN directly
            if icomTrx.icomTrxCivAdress == 162:
                icomTrx.setFrequenceOffUnselectVFO(up)
            else:
                icomTrx.setVFO('VFOB')
                icomTrx.setFrequence(up)
                icomTrx.setVFO('VFOA')

    def setDownlinkSimplex(self, dw):
        if icomTrx.isPttOff():
            icomTrx.setVFO('VFOA')
            icomTrx.setFrequence(str(int(dw) + int(self.rit)))

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        try:
            with open('satellites.txt', 'r') as fp:
                for line in fp:
                    new_satellite = Satellite()
                    new_satellite.name = line.split(",")[0] + " " + line.split(",")[1]
                    new_satellite.mode = line.split(",")[1]
                    new_satellite.rit = line.split(",")[2]
                    new_satellite.satmode = line.split(",")[3].replace("\n", "").upper()
                    self.satellites.append(new_satellite)
        finally:
            fp.close()

        layout = QGridLayout()

        comboSatellite = QComboBox(self)
        for sat in self.satellites:
            comboSatellite.addItem(sat.name)
        comboSatellite.currentTextChanged.connect(self.on_combobox_changed)

        buttonRitUp = QPushButton("RIT +25Hz")
        buttonRitUp.pressed.connect(self.setRitUp)

        buttonRitDown = QPushButton("RIT -25Hz")
        buttonRitDown.pressed.connect(self.setRitDown)

        self.ritLabel = QLabel(self)

        layout.addWidget(comboSatellite, 0, 0)

        layout.addWidget(buttonRitUp, 1, 0)
        layout.addWidget(buttonRitDown, 1, 1)
        layout.addWidget(self.ritLabel, 1, 2)

        radiobutton = QRadioButton('Sat constant')
        radiobutton.setChecked(True)
        radiobutton.country = 'Sat constant'
        radiobutton.setToolTip('Frequency on satellite transponder will be held constant')
        radiobutton.toggled.connect(self.onRadioButtonSatelliteConstantClicked)
        layout.addWidget(radiobutton, 4, 0)

        radiobutton = QRadioButton('Downlink constant')
        radiobutton.setChecked(False)
        radiobutton.country = 'Downlink constant'
        radiobutton.setToolTip('Frequency on the downlink will be held constant')
        radiobutton.toggled.connect(self.onRadioButtonDownlinkConstantClicked)
        layout.addWidget(radiobutton, 4, 1)

        w = QWidget()
        w.setLayout(layout)

        self.setWindowTitle('Gpredict with IC-9100/9700')
        self.setCentralWidget(w)
        self.show()

        self.threadpool = QThreadPool()

        worker = Worker(self.execute_main_loop)  # Any other args, kwargs are passed to the run function
        # Execute
        self.threadpool.start(worker)

    def onRadioButtonDownlinkConstantClicked(self):
        self.isDownlinkConstant = True

    def onRadioButtonSatelliteConstantClicked(self):
        self.isDownlinkConstant = False

    def on_combobox_changed(self, value):
        for sat in self.satellites:
            if sat.name == value:
                self.isLoopActive = False
                time.sleep(0.5)

                icomTrx.setSatelliteMode(False)
                icomTrx.setDualWatch(True)

                # set correct bands in SUB and MAIN für U/U, U/V, etc
                satModeArray = sat.satmode.split('/')
                self.activateCorrectUplinkBandInMain(satModeArray[0])
                if satModeArray[0] != satModeArray[1]:
                    self.isSatelliteDuplex = True
                else:
                    self.isSatelliteDuplex = False

                self.rit = int(sat.rit)

                if self.isSatelliteDuplex:
                    if sat.mode == 'SSB':
                        self.setStartSequenceSatellite('LSB')
                    if sat.mode == 'CW':
                        self.setStartSequenceSatellite('CW')
                    if sat.mode == 'FM':
                        self.setStartSequenceSatellite('FM')
                else:
                    if sat.mode == 'FM':
                        self.setStartSequenceSimplex('FM')
                    if sat.mode == 'FM-D':
                        self.setStartSequenceSimplex('FM-D')
                    if sat.mode == 'SSB-D':
                        self.setStartSequenceSimplex('SSB-D')

                self.isLoopActive = True
                break

    def execute_main_loop(self, progress_callback):
        uplink = '0'
        downlink = '0'
        last_uplink = '0'
        last_downlink = '0'
        actual_sub_frequency = ''

        debug = False
        if len(sys.argv) > 1:
            if sys.argv[1].upper() == '-DEBUG':
                debug = True

        ###############################################
        # start socket for gpredict
        ###############################################

        # start tcp server
        sock_gpredict = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock_gpredict.bind((self.HOST, self.PORT_SERVER))
        sock_gpredict.listen(1)

        ###############################################
        # create and open sockets for gqrx VHF, UHF, and SHF
        ###############################################

        sock_gqrx_vhf = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        port_vhf_open = sock_gqrx_vhf.connect_ex((self.HOST, self.PORT_GQRX_VHF))
        if port_vhf_open == 0:
            print('Connected to VHF Gqrx port.')
        else:
            print('Not connected to VHF Gqrx port.')
        sock_gqrx_uhf = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        port_uhf_open = sock_gqrx_uhf.connect_ex((self.HOST, self.PORT_GQRX_UHF))
        if port_uhf_open == 0:
            print('Connected to UHF Gqrx port.')
        else:
            print('Not connected to UHF Gqrx port.')
        sock_gqrx_shf = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        port_shf_open = sock_gqrx_shf.connect_ex((self.HOST, self.PORT_GQRX_SHF))
        if port_shf_open == 0:
            print('Connected to SHF Gqrx port.')
        else:
            print('Not connected to SHF Gqrx port.')

        ###############################################
        # main loop
        ###############################################

        while True:
            conn, addr = sock_gpredict.accept()
            print('Connected to Gpredict at:', addr)
            while 1:
                if self.isLoopActive:
                    try:
                        data = conn.recv(1000)
                        if debug:
                            print('\n###### LOOP START')
                            print('> gpredict: ' + data.decode('utf-8').replace('\n', ''))
                            print('> icom:', icomTrx.getWhatFrequencyIcomSendUs())
                        if not data:
                            break
                        if self.rit != self.last_rit:
                            if self.isSatelliteDuplex:
                                icomTrx.setVFO('SUB')
                            else:
                                icomTrx.setVFO('MAIN')
                                icomTrx.setVFO('VFOA')
                            # get the rig's downlink frequency, subtract old RIT, add new RIT and send that to the radio
                            actual_sub_frequency = icomTrx.getFrequence()
                            actual_downlink_frequency = str(int(actual_sub_frequency) - int(self.last_rit))
                            if self.isSatelliteDuplex:
                                MainWindow.setDownlink(self, actual_downlink_frequency)
                            else:
                                MainWindow.setDownlinkSimplex(self, actual_downlink_frequency)
                            # gqrx part
                            b = bytearray()
                            b.extend(map(ord, 'F ' + str(int(actual_downlink_frequency) + int(self.rit)) + '\n'))
                            if actual_downlink_frequency[1] == '4' and port_vhf_open == 0:
                                sock_gqrx_vhf.sendall(b)
                            elif actual_downlink_frequency[1] == '3' and port_uhf_open == 0:
                                sock_gqrx_uhf.sendall(b)
                            elif actual_downlink_frequency[1] == '2' and port_shf_open == 0:
                                sock_gqrx_shf.sendall(b)
                            self.last_rit = self.rit
                            self.ritLabel.setText(str(self.rit))
                        if data[0] in [70, 73]:  # I, F
                            # get downlink and uplink from gpredict
                            # and set downlink and uplink to icom
                            cut = data.decode('utf-8').split(' ')
                            if data[0] == 70:  # F - gpredict want to set Downlink
                                if self.isDownlinkConstant:
                                    downlink = last_downlink
                                else:
                                    downlink = cut[len(cut) - 1].replace('\n', '')
                            if data[0] == 73:  # I - gpredict want to set Uplink
                                uplink = cut[len(cut) - 1].replace('\n', '')
                            if debug:
                                print('>> gp2icom: last  ^ ' + last_uplink + ' v ' + last_downlink)
                                print('>> gp2icom: fresh ^ ' + uplink + ' v ' + downlink)
                            # only if uplink or downlink changed > 0 10Hz Column, then update
                            if (abs(int(last_uplink) - int(uplink)) > self.FREQUENCY_OFFSET_UPLINK):
                                if self.isSatelliteDuplex:
                                    MainWindow.setUplink(self, uplink)
                                else:
                                    MainWindow.setUplinkSimplex(self, uplink)
                                last_uplink = uplink
                                # # gqrx part
                                if self.isSatelliteDuplex:
                                    b = bytearray()
                                    b.extend(map(ord, 'F ' + uplink + '\n'))
                                    if uplink[1] == '4' and port_vhf_open == 0:
                                        sock_gqrx_vhf.sendall(b)
                                    elif uplink[1] == '3' and port_uhf_open == 0:
                                        sock_gqrx_uhf.sendall(b)
                                    elif uplink[1] == '2' and port_shf_open == 0:
                                        sock_gqrx_shf.sendall(b)
                            if not self.isDownlinkConstant:
                                if (abs(int(last_downlink) - int(downlink)) > self.FREQUENCY_OFFSET_DOWNLINK):
                                    if self.isSatelliteDuplex:
                                        MainWindow.setDownlink(self, downlink)
                                    else:
                                        MainWindow.setDownlinkSimplex(self, downlink)
                                    # gqrx part
                                    b = bytearray()
                                    b.extend(map(ord, 'F ' + str(int(downlink) + int(self.rit)) + '\n'))
                                    if downlink[1] == '4' and port_vhf_open == 0:
                                        sock_gqrx_vhf.sendall(b)
                                    elif downlink[1] == '3' and port_uhf_open == 0:
                                        sock_gqrx_uhf.sendall(b)
                                    elif downlink[1] == '2' and port_shf_open == 0:
                                        sock_gqrx_shf.sendall(b)
                                    last_downlink = downlink
                            conn.send(b'RPRT 0')  # Return Data OK to gpredict
                        elif data[0] in [102, 105]:  # i, f
                            # read downlink or uplink from icom
                            # and send it to gpredict
                            if not self.isSatelliteDuplex:
                                conn.send(b'RPRT')
                            else:
                                if data[0] == 102:  # f - gpredict ask for downlink
                                    if debug:
                                        print('>> gpredict: ask for downlink')
                                    actual_sub_frequency = icomTrx.getFrequence()
                                    if len(actual_sub_frequency) > 0 and actual_sub_frequency[0:2] in ['14', '43', '12']:
                                        downlink = str(int(actual_sub_frequency) - int(self.rit))
                                        b = bytearray()
                                        b.extend(map(ord, str(int(actual_sub_frequency) - int(self.rit)) + '\n'))
                                        conn.send(b)
                                        b = bytearray()
                                        b.extend(map(ord, 'F ' + str(int(downlink) + int(self.rit)) + '\n'))
                                        if downlink[1] == '4' and port_vhf_open == 0:
                                            sock_gqrx_vhf.sendall(b)
                                        elif downlink[1] == '3' and port_uhf_open == 0:
                                            sock_gqrx_uhf.sendall(b)
                                        elif downlink[1] == '2' and port_shf_open == 0:
                                            sock_gqrx_shf.sendall(b)
                                    else:
                                        conn.send(b'RPRT')
                                elif data[0] == 105:  # i - gpredict ask for uplink
                                    b = bytearray()
                                    b.extend(map(ord, uplink + '\n'))
                                    conn.send(b)
                        elif data[0] == 116:  # t ptt
                            conn.send(b'0')
                        else:
                            conn.send(b'RPRT 0')  # Return Data OK to gpredict
                    except Exception as e:
                        print('SUB FREQUENCY: ' + actual_sub_frequency)
                        print('DOWNLINK: ' + downlink)
                        exc_type, exc_obj, tb = sys.exc_info()
                        f = tb.tb_frame
                        lineno = tb.tb_lineno
                        filename = f.f_code.co_filename
                        linecache.checkcache(filename)
                        line = linecache.getline(filename, lineno, f.f_globals)
                        print('EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj))
                        print('connection maybe corrupt or failure in loop: close connection')
                        conn.close()
                        break
            conn.close()
            print('Connection to Gpredict closed.')

    def setRitUp(self):
        self.rit += 25
        self.ritLabel.setText(str(self.rit))

    def setRitDown(self):
        self.rit -= 25
        self.ritLabel.setText(str(self.rit))


icomTrx = icom.icom('/dev/ic9700a', '115200', 162)
app = QApplication([])
window = MainWindow()
app.exec_()
icomTrx.close()
