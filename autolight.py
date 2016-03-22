#!/usr/bin/env python

'''
 Program name: autolight.py

 v1.0 - New release.
 v2.0 - 1. Add FTP function to upload the images.
 v2.1 - 1. Change procedure to check light by working time and leaving time.
        2. The interval of taking pictures is depanding on working time and leaving time.
'''

import os, sys
import string, re
import socket
import time

import RPi.GPIO as GPIO
import serial, json

import autolightconfig
import AutoCamera

class AutoDetectMotion:
    def __init__(self, prgname, pathname, runtype):
        self.workdir = pathname
        syscon = autolightconfig.GetSysconfig()
        self.sysinfo = syscon.GetConfig()

        ### Host information
        self.hostname = socket.gethostname()
        if self.hostname == '':
            self.hostname = self.sysinfo['HOSTNAME']

        ### Run type
        if runtype == '':
            self.runtype = self.sysinfo['RUNTYPE']
        else:
            self.runtype = runtype

        ### Image directory
        self.imgdir = '%s/%s'%(self.workdir, self.sysinfo['IMGDIR'])
        if not os.path.isdir(self.imgdir):
            os.mkdir(self.imgdir)

        ### Working time
        self.worktime1 = self.sysinfo['WORKTIME1']
        self.worktime2 = self.sysinfo['WORKTIME2']

        ### FTP Information
        self.ftpaction = self.sysinfo['FTPACTION']
        self.ftphost = self.sysinfo['FTPHOST']
        self.ftpuser = self.sysinfo['FTPUSER']
        self.ftppass = self.sysinfo['FTPPASS']

        ### Camera settings
        self.preview = int(self.sysinfo['PREVIEW'])
        res = string.split(self.sysinfo['RESOLUTION'], 'x')
        #print res
        self.resolution = tuple([int(res[0]), int(res[1])])
        #print self.resolution, type(self.resolution)
        #sys.exit(0)
        self.framerate = self.sysinfo['FRAMERATE']
        self.imgiso = int(self.sysinfo['IMGISO'])

        ###
        if self.runtype not in ['picture', 'vedio']:
            usbhostport = self.sysinfo['USBHOSTPORT']
            self.usbport = serial.Serial(usbhostport, baudrate=9600, timeout=15.0)
        else:
            self.usbport = ''
        self.EnableCamera = self.sysinfo['CAMERA']
        self.TPNOPIR = int(self.sysinfo['TPNOPIR'])
        self.TPPIR = int(self.sysinfo['TPPIR'])
        self.vediotime = int(self.sysinfo['VEDIOTIME'])
        self.LIGHT = int(self.sysinfo['LIGHT_PIN'])
        ### min --> max, F is off
        self.LightLevelList = string.split(self.sysinfo['LightLevelList'], ',')
        self.LightInterval = int(self.sysinfo['LightInterval'])
        self.LightTurnoffTime = int(self.sysinfo['LightTurnoffTime'])

        ### PIR Settings
        self.PIRInterval = int(self.sysinfo['PIRInterval'])
        self.PIR = int(self.sysinfo['PIR_PIN'])

        ### Ping Settings
        self.maxdistance = int(self.sysinfo['MAXDISTANCE'])
        self.TRIG = int(self.sysinfo['PING_TRIG'])
        self.ECHO = int(self.sysinfo['PING_ECHO'])

        ### Log file
        self.logdir = '%s/logfile'%self.workdir
        if not os.path.isdir(self.logdir):
            os.mkdir(self.logdir)
        self.logfile = '%s/autolight.log'%self.logdir

    def Start(self):
        ### Defing working hour
        workstart1, workstop1 = string.split(self.worktime1, '-')
        workstart2, workstop2 = string.split(self.worktime2, '-')

        try:
            print 'Run mode:  ', self.runtype
            if self.runtype in ['picture', 'vedio']:
                self.RunOnCamera(workstart1, workstop1, workstart2, workstop2)
            elif self.runtype == 'type1':
                self.RunOnType(workstart1, workstop1, workstart2, workstop2)
        except Exception, err:
            print 'Error:  ', err

    def RunOnCamera(self, workstart1, workstop1, workstart2, workstop2):
        try:
            while True:
                chkworktime = time.strftime('%H:%M', time.localtime())
                #print chkworktime, workstart1, workstop1, workstart2, workstop2
                if workstart1 < chkworktime < workstop1 or workstart2 < chkworktime < workstop2:
                    LightLevel = 'A'
                    TPInterval = self.TPPIR
                    chktptime = int(time.time() % TPInterval)
                    #print time.time(), TPInterval, chktptime, self.EnableCamera
                    if chktptime == 0 and self.EnableCamera != 'False':
                        self.TakePicture(self.runtype, LightLevel)
                else:
                    LightLevel = 'E'
                    TPInterval = self.TPNOPIR
                    chktptime = int(time.time() % TPInterval)
                    #print time.time(), TPInterval, chktptime, self.EnableCamera
                    if chktptime == 0 and self.EnableCamera != 'False':
                        self.TakePicture('vedio', LightLevel)
                time.sleep(0.5)
        except KeyboardInterrupt:
            print ' Quit'
            self.WriteLogFile('Quit')
            self.CleanGPIO()
        except:
            print ' Error out'
            self.WriteLogFile('Error')
            self.CleanGPIO()

        return

    def RunOnType(self, workstart1, workstop1, workstart2, workstop2):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.PIR, GPIO.IN)
        GPIO.setup(self.TRIG, GPIO.OUT)
        GPIO.setup(self.ECHO, GPIO.IN)
        GPIO.setup(self.LIGHT, GPIO.OUT)

        msg1 = ''
        msg2 = ''
        gesture = 0
        pirstat = 0
        totaldistance = 0
        WorkLevel = 0
        LightLevel = 'F'
        pirstart = int(time.time())
        try:
            msg1 = 'System initial, turn off the light! (%s)'%(LightLevel)
            self.usbport.write(LightLevel)
            print msg1
            self.WriteLogFile(msg1)
            while True:
                nowtime = time.strftime('%H:%M:%S', time.localtime())
                chkworktime = time.strftime('%H:%M', time.localtime())
                workday = time.strftime('%w', time.localtime())
                ### Check Sensor
                usbstat = self.readlineCR(self.usbport)
                if len(usbstat) > 0 and self.is_json(usbstat):   ### and gesture in [0, 3]:
                    sensordata = json.loads(usbstat)
                    gesture = sensordata['Gesture']
                #print 'Gesture:  ', gesture
                ### Check PIR
                pirstop = int(time.time())
                pirdiff = pirstop - pirstart
                pirstat = GPIO.input(self.PIR)
                ### Check Distance
                #distance = self.GetDistance(GPIO)
                #print 'PIR:  %s , Distance:  %s  (%s)  , WorkLevel:  %s'%(pirstat, distance, nowtime, WorkLevel)
                #print '%s = %s - %s'%(pirdiff, pirstop, pirstart)
                WorkLevel = self.GetWorkLevel(WorkLevel, workday, chkworktime)
                #if pirstat == 0 and WorkLevel == 0:
                #    LightLevel = 'F'
                #    msg1 = 'System initial, turn off the light! (%s)'%(LightLevel)
                if workday in ['0', '6']:
                    if gesture == 3:
                        if LightLevel == 'F':
                            pirstart = int(time.time())
                            pirstop = int(time.time())
                            pirdiff = pirstop - pirstart
                        LightLevel = self.GetLightLevel(pirdiff, self.LightInterval)
                        if LightLevel != 'A':
                            msg1 = 'User turn on the light! (%s) (%s)'%(LightLevel, WorkLevel)
                        else:
                            msg1 = 'User keep on the light! (%s) (%s)'%(LightLevel, WorkLevel)
                    elif gesture == 4:
                        LightLevel = 'F'
                        #gesture = 0
                        msg1 = 'User turn off the light! (%s) (%s)'%(LightLevel, WorkLevel)
                    elif pirstat == 0:
                        if pirdiff > self.LightTurnoffTime:
                            LightLevel = 'F'
                            msg1 = 'People is leaved, turn off the light! (%s) (%s)'%(LightLevel, WorkLevel)
                            #print 'Distance average:  %s '%(totaldistance / self.PIRInterval)
                        elif LightLevel != 'F':
                            LightLevel = self.GetLightLevel(pirdiff, self.LightInterval)
                            #totaldistance += distance
                            if LightLevel != 'A':
                                msg1 = 'Increase the light to %s in %s seconds (%s)'%(LightLevel, self.LightInterval, WorkLevel)
                            else:
                                msg1 = 'Keep the light on  %s in %s seconds (%s)'%(LightLevel, self.LightTurnoffTime, WorkLevel)
                        elif LightLevel == 'F':
                            msg1 = 'Weekend and turn off the light! (%s) (%s)'%(LightLevel, WorkLevel)
                    elif pirstat == 1:
                        if LightLevel == 'F':
                            pirstart = int(time.time())
                            pirstop = int(time.time())
                            pirdiff = pirstop - pirstart
                        LightLevel = self.GetLightLevel(pirdiff, self.LightInterval)
                        if LightLevel != 'A':
                            msg1 = 'Detected people is coming, turn on the light! (%s) (%s)'%(LightLevel, WorkLevel)
                        else:
                            msg1 = 'Detected people is coming, keep to light on! (%s) (%s)'%(LightLevel, WorkLevel)
                else:
                    #if WorkLevel == 3:
                    if chkworktime == workstop1:
                        LightLevel = 'F'
                        msg1 = 'Lunch time, turn off the light! (%s) (%s)'%(LightLevel, WorkLevel)
                    #elif WorkLevel == 4 and LightLevel == 'F':
                    elif WorkLevel == 3:
                        if gesture == 3:
                            if LightLevel == 'F':
                                pirstart = int(time.time())
                                pirstop = int(time.time())
                                pirdiff = pirstop - pirstart
                            LightLevel = self.GetLightLevel(pirdiff, self.LightInterval)
                            if LightLevel != 'A':
                                msg1 = 'User turn on the light! (%s) (%s)'%(LightLevel, WorkLevel)
                            else:
                                msg1 = 'User keep on the light! (%s) (%s)'%(LightLevel, WorkLevel)
                        elif gesture == 4:
                            LightLevel = 'F'
                            #gesture = 0
                            msg1 = 'User turn off the light! (%s) (%s)'%(LightLevel, WorkLevel)
                        else:
                            LightLevel = 'F'
                            if pirstat == 0:
                                msg1 = 'Lunch time and people is not coming, turn on the light! (%s) (%s)'%(LightLevel, WorkLevel)
                            else:
                                msg1 = 'Lunch time and detected people is coming, but do not turn on the light! (%s) (%s)'%(LightLevel, WorkLevel)
                    elif chkworktime == workstart2:
                        LightLevel = 'E'
                        pirstart = int(time.time())
                        pirstop = int(time.time())
                        pirdiff = pirstop - pirstart
                        msg1 = 'Working hour and turn on the light! (%s) (%s)'%(LightLevel, WorkLevel)
                    elif pirstat == 1 and WorkLevel != 3:
                        if LightLevel == 'F':
                            pirstart = int(time.time())
                            pirstop = int(time.time())
                            pirdiff = pirstop - pirstart
                        LightLevel = self.GetLightLevel(pirdiff, self.LightInterval)
                        if LightLevel != 'A':
                            msg1 = 'Detected people is coming, turn on the light! (%s) (%s)'%(LightLevel, WorkLevel)
                        else:
                            msg1 = 'Detected people is coming, keep to light on! (%s) (%s)'%(LightLevel, WorkLevel)
                            #msg1 = 'Detected people is coming, turn on the light! (%s) (%s)'%(LightLevel, distance)
                    elif (gesture in [3, 4] or pirstat == 0) and WorkLevel not in [2, 4]:
                        if pirdiff > self.LightTurnoffTime:
                            if gesture == 3:
                                if LightLevel == 'F':
                                    pirstart = int(time.time())
                                    pirstop = int(time.time())
                                    pirdiff = pirstop - pirstart
                                LightLevel = self.GetLightLevel(pirdiff, self.LightInterval)
                                if LightLevel != 'A':
                                    msg1 = 'User turn on the light! (%s) (%s)'%(LightLevel, WorkLevel)
                                else:
                                    msg1 = 'User keep on the light! (%s) (%s)'%(LightLevel, WorkLevel)
                            elif gesture == 4:
                                LightLevel = 'F'
                                #gesture = 0
                                msg1 = 'User turn off the light! (%s) (%s)'%(LightLevel, WorkLevel)
                            else:
                                LightLevel = 'F'
                                msg1 = 'People is leaved, turn off the light! (%s) (%s)'%(LightLevel, WorkLevel)
                                #print 'Distance average:  %s '%(totaldistance / self.PIRInterval)
                        elif LightLevel != 'F':
                            LightLevel = self.GetLightLevel(pirdiff, self.LightInterval)
                            #totaldistance += distance
                            if LightLevel != 'A':
                                msg1 = 'Increase the light to %s in %s seconds (%s)'%(LightLevel, self.LightInterval, WorkLevel)
                            else:
                                msg1 = 'Keep the light on  %s in %s seconds (%s)'%(LightLevel, self.LightTurnoffTime, WorkLevel)
                    elif (gesture in [3, 4] or pirstat == 0) and WorkLevel in [2, 4]:
                        if gesture == 3:
                            if LightLevel == 'F':
                                pirstart = int(time.time())
                                pirstop = int(time.time())
                                pirdiff = pirstop - pirstart
                            LightLevel = self.GetLightLevel(pirdiff, self.LightInterval)
                            if LightLevel != 'A':
                                msg1 = 'User turn on the light! (%s) (%s)'%(LightLevel, WorkLevel)
                            else:
                                msg1 = 'User keep on the light! (%s) (%s)'%(LightLevel, WorkLevel)
                        elif gesture == 4:
                            LightLevel = 'F'
                            #gesture = 0
                            msg1 = 'User turn off the light! (%s) (%s)'%(LightLevel, WorkLevel)
                        else:
                            if LightLevel != 'F':
                                LightLevel = self.GetLightLevel(pirdiff, self.LightInterval)
                                if LightLevel != 'A':
                                    msg1 = 'Increase the light to %s in %s seconds (%s)'%(LightLevel, self.LightInterval, WorkLevel)
                                else:
                                    msg1 = 'Working hour and keep the light on! (%s) (%s)'%(LightLevel, WorkLevel)
                            else:
                                LightLevel = 'F'
                                msg1 = 'Working hour and people is not coming, turn off the light! (%s) (%s)'%(LightLevel, WorkLevel)
                    #elif WorkLevel == 4 and LightLevel == 'F' and pirstat == 1:
                    #    LightLevel = 'E'
                    #    pirstart = int(time.time())
                    #    pirstop = int(time.time())
                    #    pirdiff = pirstop - pirstart
                    #    msg1 = 'Working hour and turn on the light! (%s)'%(LightLevel)
                    else:
                        msg1 = 'Undefined status'

                ### Taking pictures
                if LightLevel != 'F':
                    TPInterval = self.TPPIR
                    LightStat = 1
                else:
                    TPInterval = self.TPNOPIR
                    LightStat = 0

                chktptime = int(time.time() % TPInterval)
                #print time.time(), TPInterval, chktptime
                if chktptime == 0 and self.EnableCamera != 'False':
                    #print time.time(), TPInterval, chktptime
                    self.TakePicture(self.runtype, LightLevel)

                if msg1 != msg2:
                    print '%s: %s'%(nowtime, msg1)
                    self.WriteLogFile(msg1)
                    #self.TakePicture(self.runtype, LightLevel)
                    msg2 = msg1
                    self.LightOperation(GPIO, LightStat, LightLevel)
                    self.usbport.write(LightLevel)

                #time.sleep(0.5)
        except KeyboardInterrupt:
            print ' Quit'
            self.WriteLogFile('Quit')
            self.CleanGPIO()
        except:
            print ' Error out'
            self.WriteLogFile('Error')
            self.CleanGPIO()

        return

    def GetWorkLevel(self, WorkLevel, workday, chkworktime):    
        ### Defing working hour
        workstart1, workstop1 = string.split(self.worktime1, '-')
        workstart2, workstop2 = string.split(self.worktime2, '-')

        if workday in ['0', '6']:
            if WorkLevel != 6:
                workmsg = 'Weekend'
                print workmsg
                self.WriteLogFile(workmsg)
            WorkLevel = 6
        else:
            if chkworktime < workstart1:
                if WorkLevel != 1:
                    workmsg = 'Before working time (%s < %s)'%(chkworktime, workstart1)
                    print workmsg
                    self.WriteLogFile(workmsg)
                WorkLevel = 1
            elif workstart1 <= chkworktime < workstop1:
                if WorkLevel != 2:
                    workmsg = 'Morning working time (%s < %s < %s)'%(workstart1, chkworktime, workstop1)
                    print workmsg
                    self.WriteLogFile(workmsg)
                WorkLevel = 2
            elif workstop1 <= chkworktime < workstart2:
                if WorkLevel != 3:
                    workmsg = 'Lunch time (%s < %s < %s)'%(workstop1, chkworktime, workstart2)
                    print workmsg
                    self.WriteLogFile(workmsg)
                WorkLevel = 3
            elif workstart2 <= chkworktime < workstop2:
                if WorkLevel != 4:
                    workmsg = 'Afternoon working time (%s < %s < %s)'%(workstart2, chkworktime, workstop2)
                    print workmsg
                    self.WriteLogFile(workmsg)
                WorkLevel = 4
            elif workstop2 < chkworktime:
                if WorkLevel != 5:
                    workmsg = 'After working time (%s < %s)'%(workstop2, chkworktime)
                    print workmsg
                    self.WriteLogFile(workmsg)
                WorkLevel = 5

        return WorkLevel

    def LightOperation(self, gpio, lightstat, lightlevel):
        ### Method 1
        #gpio.output(self.LIGHT, lightstat)
        ### Method 2
        lightsleep = 0.1
        if lightlevel == 'A':
            lidmaxno = 5
        elif lightlevel == 'B':
            lidmaxno = 4
        elif lightlevel == 'C':
            lidmaxno = 3
        elif lightlevel == 'D':
            lidmaxno = 2
        elif lightlevel == 'E':
            lidmaxno = 1

        if lightlevel != 'F':
            lid = 1
            while True:
                gpio.output(self.LIGHT, lightstat)
                time.sleep(lightsleep)
                gpio.output(self.LIGHT, 0)
                time.sleep(lightsleep)
                if lid > lidmaxno:
                    gpio.output(self.LIGHT, lightstat)
                    break
                lid += 1
            #print lightlevel, lid
        elif lightlevel == 'F':
            gpio.output(self.LIGHT, lightstat)

        return

    def GetLightLevel(self, pirdiff, lightinterval):
        chkstat = int(pirdiff / lightinterval)
        if chkstat <= 1:
            LightLevel = 'E'
        elif chkstat <= 2:
            LightLevel = 'D'
        elif chkstat <= 3:
            LightLevel = 'C'
        elif chkstat <= 4:
            LightLevel = 'B'
        elif chkstat >= 5:
            LightLevel = 'A'
        else:
            LightLevel = 'F'

        return LightLevel

    def TakePicture(self, runtype, LightLevel):
        currentTime = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        uptime = time.strftime('%Y%m%d_%H%M%S', time.localtime())
        ftptxt = '%s/%s.txt'%(self.imgdir, uptime)
        camera = AutoCamera.AutoCamera(self.ftpaction, runtype, self.hostname)
        if runtype == 'picture':
            imgname = "%s/%s_%s.jpg"%(self.imgdir, currentTime, LightLevel)
            ftpstat, ftpmsg = camera.TakePicture(imgname, self.resolution)
        elif runtype == 'vedio':
            imgname = "%s/%s_%s.h264"%(self.imgdir, currentTime, LightLevel)
            newimgname = "%s/%s_%s.mp4"%(self.imgdir, currentTime, LightLevel)
            ftpstat, ftpmsg = camera.TakeVedio(self.vediotime, self.framerate, ftptxt, imgname, newimgname)

        if ftpmsg != '':
            self.WriteLogFile(ftpmsg)

        return

    def WriteLogFile(self, writemsg):
        wfile = open(self.logfile, 'a+')
        wfile.write('%s\n'%writemsg)
        wfile.close()

        return

    def GetHostname(self):
        try:
            a, b = os.popen2('hostname')
            hostname = string.split(b.read(), '\n')[0]
        except:
            hostname = 'autolight'

        return hostname

    def GetDistance(self, gpio):
        gpio.output(self.TRIG, True)
        time.sleep(0.001)
        gpio.output(self.TRIG, False)

        count = 5000
        while gpio.input(self.ECHO) != True and count > 0:
            count -= 1
        send_start = time.time()

        count = 5000
        while gpio.input(self.ECHO) != False and count > 0:
            count -= 1
        send_recv = time.time()

        pulse_len = send_recv - send_start
        #distance = round(pulse_len * 340 * 100 / 2, 2)
        distance = int(pulse_len * 340 * 100 / 2)

        return distance

    def CheckDistance(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.TRIG, GPIO.OUT)
        GPIO.setup(self.ECHO, GPIO.IN)

        GPIO.output(self.TRIG, True)
        time.sleep(0.001)
        GPIO.output(self.TRIG, False)

        count = 5000
        while GPIO.input(self.ECHO) != True and count > 0:
            count -= 1
        send_start = time.time()

        count = 5000
        while GPIO.input(self.ECHO) != False and count > 0:
            count -= 1
        send_recv = time.time()

        pulse_len = send_recv - send_start
        #distance = round(pulse_len * 340 * 100 / 2, 2)
        distance = int(pulse_len * 340 * 100 / 2)

        self.CleanGPIO()

        return distance

    def CleanGPIO(self):
        try:
            GPIO.cleanup()
        except:
            pass

        return

    def readlineCR(self, port):
        rv = ""
        while True:
            ch = port.read()
            rv += ch
            if ch in ['\r', '']:
                return rv

    def is_json(self, myjson):
        try:
            json_object = json.loads(myjson)
        except ValueError, e:
            return False

        return True

if __name__ == '__main__':
    runtype = ''
    prgname = sys.argv[0]
    pathname = os.path.abspath(os.path.dirname(prgname))
    optsinfo = sys.argv[1:]

    if optsinfo:
        if optsinfo[0] in ['picture', 'vedio', 'type1']:
            runtype = optsinfo[0]

    app = AutoDetectMotion(prgname, pathname, runtype)
    app.Start()

