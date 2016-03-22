#!/usr/bin/env python

'''
 Program name: AutoCamera.py

 v1.0 - New release.

'''

import os, sys
import string, re
import time
import socket

import picamera
import AutoFTP
import ExecuteSubprocess
import autolightconfig

class AutoCamera():
    def __init__(self, ftpaction, runtype, hostname):
        syscon = autolightconfig.GetSysconfig()
        self.sysinfo = syscon.GetConfig()
        self.ftphost = self.sysinfo['FTPHOST']
        self.ftpuser = self.sysinfo['FTPUSER']
        self.ftppass = self.sysinfo['FTPPASS']
        self.ftpaction = ftpaction
        self.runtype = runtype
        self.hostname = hostname

    def TakePicture(self, imgname, resolution):
        ftpstat = 1
        ftpmsg = ''
        try:
            print '==> Take picture:  ', imgname
            camera = picamera.PiCamera()
            camera.resolution = resolution
            camera.capture(imgname)
            camera.close()
            #print self.ftpaction
            if self.ftpaction == 'True':
                ### Upload the image files
                print '==> FTP upload picture:  ', imgname
                ftpcmd = AutoFTP.AutoFTP(self.hostname, self.ftphost, self.ftpuser, self.ftppass)
                ftpstat, ftpmsg = ftpcmd.FTPUploadFile(imgname)
                print 'FTP info:  ', ftpstat, ftpmsg
                if ftpstat == 0:
                    os.remove(imgname)
        except:
            pass

        return ftpstat, ftpmsg

    def TakeVedio(self, vediotime, framerate, ftptxt, imgname, newimgname):
        ftpstat = 1
        ftpmsg = ''
        try:
            print '==> Take vedio:  ', imgname
            vediocmd = '/usr/bin/raspivid -t %s -w 1280 -h 960 -fps %s -o %s'%(vediotime, framerate, imgname)
            # -b 3500000 -w 1280 -h 960 -fps 10 
            submode = 'batchmsg'
            sub = ExecuteSubprocess.ExecuteSubprocess()
            msg, err = sub.ExecuteSubprocess(submode, vediocmd)
            #print msg, err
            if self.ftpaction == 'True':
                ### Upload the image files
                print '==> FTP upload vedio:  ', newimgname
                ftpcmd = AutoFTP.AutoFTP(self.hostname, self.ftphost, self.ftpuser, self.ftppass)
                ftpstat, ftpmsg = ftpcmd.FTPCmdUploadFile(framerate, ftptxt, imgname, newimgname)
                print 'FTP info:  ', ftpstat, ftpmsg
        except:
            pass

        return ftpstat, ftpmsg

if __name__ == '__main__':
    runtype = ''
    imgname = ''
    hostname = socket.gethostname()
    resolution = '1600x1600'
    framerate = 10
    vediotime = 5000
    ftpaction = 'False'
    prgname = sys.argv[0]
    pathname = os.path.abspath(os.path.dirname(prgname))
    optsinfo = sys.argv[1:]
    usage = '\n  * Usage:  %s [ -t picture | vedio ] [ -r HxW ] [ -o outputfile ] [ -time N ms ] [ -f N ] [ -ftp ] '%prgname
    usage += '            -t:    type \n'
    usage += '            -r:    resolution WxH \n'
    usage += '            -o:    output file name\n'
    usage += '            -time: vedio time\n'
    usage += '            -f:    frame rate\n'
    usage += '            -ftp:  ftp upload file\n'

    if optsinfo:
        oid = 0
        for opt in optsinfo:
            if opt == '-t':
                try:
                    runtype = optsinfo[oid + 1]
                    if runtype not in ['picture', 'vedio']:
                        runtype = ''
                except:
                    pass
            if opt == '-o':
                try:
                    imgname = optsinfo[oid + 1]
                except:
                    pass
            if opt == '-r':
                try:
                    resolution = optsinfo[oid + 1]
                except:
                    pass
            if opt == '-f':
                try:
                    framerate = optsinfo[oid + 1]
                except:
                    pass
            if opt == '-time':
                try:
                    vediotime = optsinfo[oid + 1]
                except:
                    pass
            if opt == '-ftp':
                ftpaction = 'True'
            oid += 1
    else:
        print usage
        sys.exit(0)

    #print runtype, imgname
    if runtype == '':
        print usage
        sys.exit(0)

    if imgname == '':
        LightLevel = 'F'
        currentTime = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        if runtype == 'picture':
            imgname = "%s_%s.jpg"%(currentTime, LightLevel)
        elif runtype == 'vedio':
            imgname = "%s_%s.h264"%(currentTime, LightLevel)
            newimgname = "%s_%s.mp4"%(currentTime, LightLevel)
    res = string.split(resolution, 'x')
    #print res
    resolution = tuple([int(res[0]), int(res[1])])

    app = AutoCamera(ftpaction, runtype, hostname)
    if runtype == 'picture':
        app.TakePicture(imgname, resolution)
    elif runtype == 'vedio':
        app.TakeVedio(vediotime, framerate, imgname, newimgname)

