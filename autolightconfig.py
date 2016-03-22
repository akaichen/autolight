#!/usr/bin/env python

'''
 Program name: autolightconfig.py

 v1.0 - New release.

'''

import os,sys

class GetSysconfig():
    def __init__(self):
        self.sysinfo = {}

    def GetConfig(self):
        sysinfo = {}
        sysinfo['HOSTNAME'] = 'autolight1'
        ### picture, vedio, type1
        sysinfo['RUNTYPE'] = 'picture'
        sysinfo['IMGDIR'] = 'imgdir'
        sysinfo['WORKTIME1'] = '08:30-12:00'
        sysinfo['WORKTIME2'] = '13:00-17:30'
        sysinfo['FTPACTION'] = 'True'
        sysinfo['FTPHOST'] = '172.30.16.100'
        #sysinfo['FTPHOST'] = '192.168.1.100'
        sysinfo['FTPUSER'] = 'ftpuser'
        sysinfo['FTPPASS'] = 'ftpuser'
        sysinfo['USBHOSTPORT'] = '/dev/ttyUSB0'
        sysinfo['PREVIEW'] = '0'
        sysinfo['RESOLUTION'] = '1600x1600'
        sysinfo['FRAMERATE'] = '10'
        sysinfo['IMGISO'] = '400'
        sysinfo['CAMERA'] = 'True'
        sysinfo['TPNOPIR'] = '1800'
        sysinfo['TPPIR'] = '600'
        sysinfo['VEDIOTIME'] = '120000'
        sysinfo['LIGHT_PIN'] = '17'
        ### F,E,D,C,B,A
        sysinfo['LightLevelList'] = 'F,E,D,C'
        sysinfo['LightInterval'] = '10'
        sysinfo['LightTurnoffTime'] = '300'
        sysinfo['PIRInterval'] = '30'
        sysinfo['PIR_PIN'] = '7'
        sysinfo['MAXDISTANCE'] = '100'
        sysinfo['PING_TRIG'] = '23'
        sysinfo['PING_ECHO'] =  '24'

        return sysinfo

