#!/usr/bin/env python

'''
 Program name: AutoFTP.py

 v1.0 - New release.

'''

import os,sys
import time
import string,re
import socket
import ftplib

import autolightconfig
import ExecuteSubprocess

class AutoFTP():
    def __init__(self, hostname, ftphost, ftpuser, ftppass):
        syscon = autolightconfig.GetSysconfig()
        self.sysinfo = syscon.GetConfig()
        if hostname == '':
            hostname = socket.gethostname()
        self.hostname = hostname
        if ftphost == '':
            ftphost = self.sysinfo['FTPHOST']
        self.ftphost = ftphost
        if ftpuser == '':
            ftpuser = self.sysinfo['FTPUSER']
        self.ftpuser = ftpuser
        if ftppass == '':
            ftppass = self.sysinfo['FTPPASS']
        self.ftppass = ftppass

    def OnVerifyFtp(self, ftphost, ftpuser, ftppass, ftptype, ftpstat, ftpmsg):
        try:
            self.ftp = ftplib.FTP(ftphost)
            self.ftp.login(ftpuser, ftppass)
            if ftptype == 'logout':
                self.ftp.quit()
            ftpstat = 0
        except:
            ftpstat = 1
            ftpmsg += 'Error: Cannot connect to FTP Host:  %s  using account %s / %s'%(ftphost, ftpuser, ftppass) 

        return ftpstat, ftpmsg

    def FTPUploadFile(self, upfilename):
        uploadtime = time.strftime('%Y-%m-%d_%H:%M:%S', time.localtime())
        self.ftp = ''
        ftpstat = 1
        ftpmsg  = ''
        ftptype = 'nologout'
        ftpstat, ftpmsg = self.OnVerifyFtp(self.ftphost, self.ftpuser, self.ftppass, ftptype, ftpstat, ftpmsg)
        if ftpstat == 0:
            filepath, filename = os.path.split(upfilename)
            dirs = self.ftp.nlst()
            if self.hostname not in dirs:
                self.ftp.mkd(self.hostname)
            self.ftp.cwd(self.hostname)
            upfileinfo = open(upfilename, 'rb')
            self.ftp.storbinary('STOR ' + filename, upfileinfo)
            filelist = self.ftp.nlst('-l %s'%filename)
            if filelist:
                localsize = os.stat(upfilename).st_size
                ftpsize   = string.split(filelist[0])[4]
                if int(localsize) != int(ftpsize):
                    ftpstat = 1
                    ftpmsg += 'Error:  %s File size does not match (%s != %s)!'%(upfilename, localsize, ftpsize)
                else:
                    #print 'OK:     %s File size is matched!!'%upfilename
                    ftpstat = 0
                    ftpmsg += '%s: %s upload image file %s (filesize: %s)'%(uploadtime, self.hostname, upfilename, ftpsize)
            else:
                ftpstat = 1
                ftpmsg += 'Error:  %s File upload failed!'%upfilename

        self.ftp.quit()

        return ftpstat, ftpmsg

    def FTPCmdUploadFile(self, framerate, ftptxt, upfilename, newupfilename):
        uploadtime = time.strftime('%Y-%m-%d_%H:%M:%S', time.localtime())
        localsize = os.stat(upfilename).st_size
        workdir = os.path.abspath(os.path.dirname(upfilename))
        ftpstat = 0
        ftpmsg = ''
        ftptxt = self.GenFTPUploadCmd(workdir, ftptxt, newupfilename)
        ftpcmd  = '/usr/bin/MP4Box -fps %s -add %s %s && '%(framerate, upfilename, newupfilename)
        ftpcmd += '/usr/bin/ftp -i -n %s < %s &&'%(self.ftphost, ftptxt)
        ftpcmd += '/bin/rm -f %s %s %s'%(ftptxt, upfilename, newupfilename)
        #print ftpcmd
        submode = 'batch'
        sub = ExecuteSubprocess.ExecuteSubprocess()
        msg, err = sub.ExecuteSubprocess(submode, ftpcmd)
        #print msg, err
        ftpsize = localsize
        ftpmsg += '%s: %s upload image file %s '%(uploadtime, self.hostname, newupfilename)

        return ftpstat, ftpmsg

    def GenFTPUploadCmd(self, workdir, ftptxt, newupfilename):
        wfile = open(ftptxt, 'w')
        wfile.write('user %s %s\n'%(self.ftpuser, self.ftppass))
        wfile.write('bin\n')
        wfile.write('lcd %s\n'%workdir)
        wfile.write('cd %s\n'%self.hostname)
        wfile.write('put %s\n'%os.path.basename(newupfilename))
        wfile.write('quit\n')
        wfile.close()

        return ftptxt


if __name__ == '__main__':
    hostname = ''
    ftphost = ''
    ftpuser = ''
    ftppass = ''
    upfilename = ''

    prgname = sys.argv[0]
    pathname = os.path.abspath(os.path.dirname(prgname))
    optsinfo = sys.argv[1:]
    usage = '\n  * Usage:  %s [ upfilename ] [ ftphost ] [ ftpuser ] [ ftppass ] '%prgname

    if not optsinfo:
        print usage
        sys.exit(0)
    else:
        upfilename = optsinfo[0]
        ftphost = optsinfo[1]
        ftpuser = optsinfo[2]
        ftppass = optsinfo[3]

        if upfilename != '':
            app = AutoFTP(hostname, ftphost, ftpuser, ftppass)
            app.FTPUploadFile(upfilename)
