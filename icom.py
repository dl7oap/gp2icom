import serial
import time

class ic9700:

    def __init__(self, serialDevice, serialBaud):
        self.serialDevice = serialDevice
        self.serialBaud = serialBaud
        # start serial usb connection
        self.ser = serial.Serial(serialDevice, serialBaud)

    # private function
    def __generateIcomCIVsetFrequence(self, freq):
        freq = '0000000000' + freq
        freq = freq[len(freq)-10:len(freq)]
        # Frequence Set IC-9700
        retFreq = chr(int(freq[8] + freq[9], 16))
        retFreq += chr(int(freq[6] + freq[7], 16))
        retFreq += chr(int(freq[4] + freq[5], 16))
        retFreq += chr(int(freq[2] + freq[3], 16))
        retFreq += chr(int(freq[0] + freq[1], 16))
        s = '\xfe\xfe\xa2\x00\x05' + retFreq + '\xfd'
        b = bytearray()
        b.extend(map(ord, s))
        return b

    # gives a empty bytearray when data crc is not valid
    def __readFromIcom(self):
        time.sleep(0.04)
        b = bytearray()
        while self.ser.inWaiting():
            b = b + self.ser.read()
        if len(b) > 0:
            # valid message
            if b[0] == 254 and b[1] == 254 and b[2] == 0 and b[3] == 162 and b[4] == 251 and b[5] == 253:
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
        print('   * readFromIcom return value: ', b)
        return b
        
    # gives a empty bytearray when data crc is not valid
    def __writeToIcom(self, b):
        s = self.ser.write(b)
        print('   * writeToIcom value: ', b)
        return self.__readFromIcom()

    def close(self):
        self.ser.close()

    def setMode(self, mode):
        mode = mode.upper()
        if mode == 'FM':
            self.__writeToIcom(b'\xfe\xfe\xa2\x00\x06\x05\x01\xfd')
        if mode == 'USB':
            self.__writeToIcom(b'\xfe\xfe\xa2\x00\x06\x01\x02\xfd')
        if mode == 'LSB':
            self.__writeToIcom(b'\xfe\xfe\xa2\x00\x06\x00\x02\xfd')
        if mode == 'CW':
            self.__writeToIcom(b'\xfe\xfe\xa2\x00\x06\x03\x01\xfd')

    def setVFO(self, vfo):
        vfo = vfo.upper()
        if vfo == 'VFOA':
            self.__writeToIcom(b'\xfe\xfe\xa2\x00\x07\x00\xfd')
        if vfo == 'VFOB':
            self.__writeToIcom(b'\xfe\xfe\xa2\x00\x07\x01\xfd')
        if vfo == 'MAIN':
            self.__writeToIcom(b'\xfe\xfe\xa2\x00\x07\xd0\xfd')  # select MAIN
        if vfo == 'SUB':
            self.__writeToIcom(b'\xfe\xfe\xa2\x00\x07\xd1\xfd')  # select SUB

    # change main and sub
    def setExchange(self):
        self.__writeToIcom(b'\xfe\xfe\xa2\x00\x07\xB0\xfd')

    # change main and sub
    def setSatelliteMode(self, on):
        if on:
            self.__writeToIcom(b'\xfe\xfe\xa2\x00\x16\x5A\x01\xfd')
        else:
            self.__writeToIcom(b'\xfe\xfe\xa2\x00\x16\x5A\x00\xfd')

    def setDualWatch(self, on):
        if on:
            self.__writeToIcom(b'\xfe\xfe\xa2\x00\x16\x59\x01\xfd')
        else:
            self.__writeToIcom(b'\xfe\xfe\xa2\x00\x16\x59\x00\xfd')

    # Parameter: hertz string with 3 numbers
    def setToneHz(self, hertz):
        s = '\xfe\xfe\xa2\x00\x1b\x00' + chr(int('0' + hertz[0], 16)) + chr(int(hertz[1] + hertz[2], 16)) + '\xfd'
        b = bytearray()
        b.extend(map(ord, s))
        self.__writeToIcom(b)
    # Parameter: hertz string with 3 numbers

    def setRitFrequence(self, value):
        hertz = '0000' + str(abs(value))
        if value >= 0:
            s = '\xfe\xfe\xa2\x00\x21\x00' + chr(int(hertz[-2] + hertz[-1], 16)) + chr(int(hertz[-4] + hertz[-3], 16)) + '\x00\xfd'
        else:
            s = '\xfe\xfe\xa2\x00\x21\x00' + chr(int(hertz[-2] + hertz[-1], 16)) + chr(int(hertz[-4] + hertz[-3], 16)) + '\x01\xfd'
        b = bytearray()
        b.extend(map(ord, s))
        self.__writeToIcom(b)

    def setFrequence(self, frequence):
        return self.__writeToIcom(self.__generateIcomCIVsetFrequence(frequence))

    def setSql(self, value):
        # parameter value 0000 to 0255 as number not as string
        squelch = '0000' + str(abs(value))
        s = '\xfe\xfe\xa2\x00\x14\x03' + chr(int('0' + squelch[-3], 16)) + chr(int(squelch[-2] + squelch[-1], 16)) + '\xfd'
        b = bytearray()
        b.extend(map(ord, s))
        self.__writeToIcom(b)

    # NF Loudness
    # Parameter value between 0000 to 0255
    def setAudioFrequenceLevel(self, value):
        loudness = '0000' + str(abs(value))
        # value 0000 to 0255
        s = '\xfe\xfe\xa2\x00\x14\x01' + chr(int('0' + loudness[-3], 16)) + chr(int(loudness[-2] + loudness[-1], 16)) + '\xfd'
        b = bytearray()
        b.extend(map(ord, s))
        self.__writeToIcom(b)

    def setToneSquelchOn(self, on):
        if on:
            self.__writeToIcom(b'\xfe\xfe\xa2\x00\x16\x43\x01\xfd')
        else:
            self.__writeToIcom(b'\xfe\xfe\xa2\x00\x16\x43\x00\xfd')

    def setToneOn(self, on):
        if on:
            self.__writeToIcom(b'\xfe\xfe\xa2\x00\x16\x42\x01\xfd')
        else:
            self.__writeToIcom(b'\xfe\xfe\xa2\x00\x16\x42\x00\xfd')

    def setAfcOn(self, on):
        if on:
            self.__writeToIcom(b'\xfe\xfe\xa2\x00\x16\x4A\x01\xfd')
        else:
            self.__writeToIcom(b'\xfe\xfe\xa2\x00\x16\x4A\x00\xfd')

    # Parameter b: True = set SPLIT ON, False = set SPLIT OFF
    def setSplitOn(self, on):
        if on:
            self.__writeToIcom(b'\xfe\xfe\xa2\x00\x0F\x01\xfd')
        else:
            self.__writeToIcom(b'\xfe\xfe\xa2\x00\x0F\x00\xfd')

    # Parameter b: True = set RIT ON, False = set RIT OFF
    def setRitOn(self, on):
        if on:
            self.__writeToIcom(b'\xfe\xfe\xa2\x00\x21\x01\x01\xfd')
        else:
            self.__writeToIcom(b'\xfe\xfe\xa2\x00\x21\x01\x00\xfd')

    def setDuplex(self, value):
        value = value.upper()
        if value == 'OFF':
            self.__writeToIcom(b'\xfe\xfe\xa2\x00\x0F\x10\xfd')
        if value == 'DUP-':
            self.__writeToIcom(b'\xfe\xfe\xa2\x00\x0F\x11\xfd')
        if value == 'DUP+':
            self.__writeToIcom(b'\xfe\xfe\xa2\x00\x0F\x12\xfd')
        if value == 'DD':
            self.__writeToIcom(b'\xfe\xfe\xa2\x00\x0F\x13\xfd')

    def getFrequence(self):
        b = self.__writeToIcom(b'\xfe\xfe\xa2\x00\x03\xfd')  # ask for used frequency
        c = ''
        if len(b) > 0:
            for a in reversed(b[5:10]):
                c = c + '%0.2X' % a
        if c[0] == '0':
            c = c[1:len(c)]
        return c

    # CI-V transceive have to be ON
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
        b = self.__writeToIcom(b'\xfe\xfe\xa2\x00\x1C\x00\xfd')  # ask for PTT status
        if b[-2] == 1:
            ret = False
        return ret

