"""
Created: by Andreas Puschendorf, DL7OAP
Date    : 09/2020

Modified: by Alex Krist, KR1ST from original by Andreas Puschendorf, DL7OAP
Date    : 11/2020
Comments: The original script has been adapted for use with the Icom IC-9100. The IC-9100 does 
          not support CAT control for RIT. I added some code to reject the echoed frames from
          the CI-V bus when "remote" jack is used on the radio rather than the USB port.

Modified: by Andreas Puschendorf, DL7OAP
Date    : 11/2020
Comments: to bring ic9100 and ic9700 together in one class the CI-V adress has to be given
          162 - default for IC9700 (162 = hex A2)
          124 - default for IC9100 (124 = hex 7C)
"""

import serial
import time


class icom:

    def __init__(self, serialDevice, serialBaud, icomTrxCivAdress):
        self.icomTrxCivAdress = icomTrxCivAdress
        self.serialDevice = serialDevice
        self.serialBaud = serialBaud
        # start serial usb connection
        self.ser = serial.Serial(serialDevice, serialBaud)

    # gives a empty bytearray when data crc is not valid
    def __readFromIcom(self):
        time.sleep(0.04)
        b = bytearray()
        while self.ser.inWaiting():
            b = b + self.ser.read()
        # drop all but the last frame
        while b.count(b'\xfd') > 1:
            del b[0:b.find(b'\xfd') + 1]
        if len(b) > 0:
            # valid message
            validMsg = bytes([254, 254, 0, self.icomTrxCivAdress, 251, 253])
            if b[0:5] == validMsg:
                b = b[6:len(b)]
                if len(b) > 0:  # read answer from icom trx
                    if b[0] == 254 and b[1] == 254 and b[-1] == 253:  # check for valid data CRC
                        return b
                    else:
                        b = bytearray()
                else:
                    b = bytearray()
            else:
                if b[0] == 254 and b[1] == 254 and b[-1] == 253:  # check for valid data CRC
                    b = b
                else:
                    b = bytearray()
        # print('   * readFromIcom return value: ', b)
        return b
        
    # gives a empty bytearray when data crc is not valid
    def __writeToIcom(self, b):
        s = self.ser.write(bytes([254, 254, self.icomTrxCivAdress, 0]) + b + bytes([253]))
        # print('   * writeToIcom value: ', b)
        return self.__readFromIcom()

    def close(self):
        self.ser.close()

    def setMode(self, mode):
        mode = mode.upper()
        if mode == 'FM':
            self.__writeToIcom(b'\x06\x05\x01')
        if mode == 'USB':
            self.__writeToIcom(b'\x06\x01\x02')
        if mode == 'LSB':
            self.__writeToIcom(b'\x06\x00\x02')
        if mode == 'CW':
            self.__writeToIcom(b'\x06\x03\x01')
        if mode == 'AM':
            self.__writeToIcom(b'\x06\x02\x01')

    def setVFO(self, vfo):
        vfo = vfo.upper()
        if vfo == 'VFOA':
            self.__writeToIcom(b'\x07\x00')
        if vfo == 'VFOB':
            self.__writeToIcom(b'\x07\x01')
        if vfo == 'MAIN':
            self.__writeToIcom(b'\x07\xd0')  # select MAIN
        if vfo == 'SUB':
            self.__writeToIcom(b'\x07\xd1')  # select SUB

    # change main and sub
    def setExchange(self):
        self.__writeToIcom(b'\x07\xB0')

    # change main and sub
    def setSatelliteMode(self, on):
        if on:
            self.__writeToIcom(b'\x16\x5A\x01')
        else:
            self.__writeToIcom(b'\x16\x5A\x00')

    def setDualWatch(self, on):
        if on:
            self.__writeToIcom(b'\x16\x59\x01')
        else:
            self.__writeToIcom(b'\x16\x59\x00')

    # Parameter: hertz string with 3 numbers
    def setToneHz(self, hertz):
        b = b'\x1b\x00' + bytes([int('0' + hertz[0], 16), int(hertz[1] + hertz[2], 16)])
        self.__writeToIcom(b)

    # Caution: RIT CI-V Command only for IC-9700, the IC-9100 has no RIT CI-V command
    # Parameter: Integer
    def setRitFrequence(self, value):
        hertz = '0000' + str(abs(value))
        if value >= 0:
            b = b'\x21\x00' + bytes([int(hertz[-2] + hertz[-1], 16),  int(hertz[-4] + hertz[-3], 16)]) + b'\x00'
        else:
            b = b'\x21\x00' + bytes([int(hertz[-2] + hertz[-1], 16),  int(hertz[-4] + hertz[-3], 16)]) + b'\x01'
        self.__writeToIcom(b)

    # Parameter as string in hertz
    def setFrequence(self, freq):
        freq = '0000000000' + freq
        freq = freq[-10:]
        b = bytes([5, int(freq[8:10], 16), int(freq[6:8], 16), int(freq[4:6], 16),
                   int(freq[2:4], 16), int(freq[0:2], 16)])
        returnMsg = self.__writeToIcom(b)
        back = False
        if len(returnMsg) > 0:
            if returnMsg.count(b'\xfb') > 0:
                back = True
        return back

    # Caution: hex 25 CI-V Command only for IC-9700
    def setFrequenceOffUnselectVFO(self, freq):
        freq = '0000000000' + freq
        freq = freq[-10:]
        b = b'\x25\x01' + bytes([int(freq[8:10], 16), int(freq[6:8], 16), int(freq[4:6], 16),
                   int(freq[2:4], 16), int(freq[0:2], 16)])
        returnMsg = self.__writeToIcom(b)
        back = False
        if len(returnMsg) > 0:
            if returnMsg.count(b'\xfb') > 0:
                back = True
        return back

    def setSql(self, value):
        # parameter value 0000 to 0255 as number not as string
        squelch = '0000' + str(abs(value))
        b = b'\x14\x03' + bytes([int('0' + squelch[-3], 16), int(squelch[-2] + squelch[-1], 16)])
        self.__writeToIcom(b)

    # NF Loudness
    # Parameter value as string between 0000 to 0255
    def setAudioFrequenceLevel(self, value):
        loudness = '0000' + str(abs(value))
        b = b'\x14\x01' + bytes([int('0' + loudness[-3], 16), int(loudness[-2] + loudness[-1], 16)])
        self.__writeToIcom(b)

    def setToneSquelchOn(self, on):
        if on:
            self.__writeToIcom(b'\x16\x43\x01')
        else:
            self.__writeToIcom(b'\x16\x43\x00')

    def setToneOn(self, on):
        if on:
            self.__writeToIcom(b'\x16\x42\x01')
        else:
            self.__writeToIcom(b'\x16\x42\x00')

    def setAfcOn(self, on):
        if on:
            self.__writeToIcom(b'\x16\x4A\x01')
        else:
            self.__writeToIcom(b'\x16\x4A\x00')

    # Parameter b: True = set SPLIT ON, False = set SPLIT OFF
    def setSplitOn(self, on):
        if on:
            self.__writeToIcom(b'\x0F\x01')
        else:
            self.__writeToIcom(b'\x0F\x00')

    # Parameter b: True = set RIT ON, False = set RIT OFF
    def setRitOn(self, on):
        if on:
            self.__writeToIcom(b'\x21\x01\x01')
        else:
            self.__writeToIcom(b'\x21\x01\x00')

    def setDuplex(self, value):
        value = value.upper()
        if value == 'OFF':
            self.__writeToIcom(b'\x0F\x10')
        if value == 'DUP-':
            self.__writeToIcom(b'\x0F\x11')
        if value == 'DUP+':
            self.__writeToIcom(b'\x0F\x12')
        if value == 'DD':
            self.__writeToIcom(b'\x0F\x13')

    def getFrequence(self):
        b = self.__writeToIcom(b'\x03')  # ask for used frequency
        c = ''
        if len(b) > 0:
            for a in reversed(b[5:10]):
                c = c + '%0.2X' % a
        if len(c) > 0: 
            if c[0] == '0':
                c = c[1:len(c)]
        return c

    # CI-V TRANSCEIVE have to be ON
    # function extract last frequency which is send to us when a user is dailing
    def getWhatFrequencyIcomSendUs(self):
        c = ''
        b = self.__readFromIcom()
        # find last CI-V message by searching from behind
        position = b.rfind(bytearray(b'\xfe\xfe'))
        if position >= 0:
            # extract answer
            answer = b[position:len(b)]
            # proof if CI-V frequence message from icom
            if len(answer) == 11 and answer[4] == 0:
                if len(answer) > 0:
                    for a in reversed(answer[5:10]):
                        c = c + '%0.2X' % a
                if c[0] == '0':
                    c = c[1:len(c)]
        return c

    def isPttOff(self):
        ret = True
        b = self.__writeToIcom(b'\x1C\x00')  # ask for PTT status
        if b[-2] == 1:
            ret = False
        return ret

