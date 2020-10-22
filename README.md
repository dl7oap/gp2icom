Author  : Andreas Puschendorf, DL7OAP
Date    : 2020-09-01


# General

This script is plugged between gpredict and ic9700 based on python 3.7.
It is listing on port 4532 for gpredict frequencies
and it is sending frequencies and startsequences for ic9700 to serial port

The main reason for this plugin or adapter is to have a smooth control of the 
ic9700 for linear ssb satellites with gpredict.
 
You can using the dail knob to sweep over the satellite transponder.
the script updates the frequencies not by time intervall, but when a specified hertz offset is reached.
this helps to avoid unnecessary updates and smooth the handling. 
you can easily store your RIT for every satellite for USB/CW, so most of the time when you start on a ssb satellite 
you will here you exactly where you want to be.

# Hints

Update rate in gpredict:
- For SIMPLEX and FM satellites i use an update rate of 10 seconds in gpredict. This is more then enough for FM.
This script will turn on AFC function for FM  on the downlink of ic9700, this eleminate, too, the doppler effect.
- For SSB/CW i use an update rate between 250ms and 800ms. So cw signals will be ok with 500ms.
When you using the main dail knob to change the frequency 2000ms feels a little bit long. Because you have
to wait until gpredict have catch the new downlink frequency and the new matching update frequency is
send to ic9700. You have to play around with this :)
But a update rate of ~30ms in gpredict will work for SSB/CW, too, with this script.

The pythonscript will only send necessary updates, to calm down the display.
Only frequency shift greater then a defined Hz will be send to the transceiver.

At start the script always set:
* with SSB the uplink in LSB and the downlink in USB. Most common satellites should work with this
* with FM subtone 670 will be activated on uplink
* using CW the uplink is mode CW and the downlink will be USB
* the script try to turn of repeater shifts (DUP+, DUP-)


# Requirements

* gpredict version 2.3.* (older should also possible)
* python 3.7 (python 2.* will not work)
* python modul pyserial and PyQt5

# Installation

- download sourcecode as zip-file https://github.com/dl7oap/gp2ic9700/archive/master.zip
- extract it to a folder of your choice
- ensure that python 3.6 or higher is installed <code>python --version</code>
- ensure that pyserial and pyqt5 is installed <code>pip install pyserial</code> and <code>pip install PyQt5</code>
- open gp2ic9700.py in a text editor, find the following line near the end <code>ic9700 = icom.ic9700('/dev/ic9700a', '19200')</code> 
and replace /dev/ic9700a with your serial connection port. Example: 'COM5' on Windows or '/dev/ttyUSB0' on Linux.
- start the script with <code>python gp2ic9700.py</code> 

Here it is working with Linux (Ubuntu) and Windows 10.

GUI:

![gui](gui.png)

# Configuration in gpredict

![gpredict](gpredict_configuration.png)

# Start the programm

Start the programm by typing this command into the shell 

<code>python gp2ic9700.py</code>  
or   
<code>pyton3 gp2ic9700.py</code>

1. select a satellite
2. start the loop
3. start gpredict with a duplex trx on port 4532 and MAIN/SUB tracking a satellite
4. editing the satellites.txt with your needs