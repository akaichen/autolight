#!/usr/bin/env python

'''
 Program name: ExecSubprocess.py

 v1.0 - New release.

'''

import os, sys
import string, re
import time
import subprocess

class ExecuteSubprocess:
    def __init__(self):
        self.subprocess = ''
        
    def ExecuteSubprocess(self, submode, cmdinfo):
        msg = ''
        err = ''
        try:
            #print 'Starting to check.....', submode, cmdinfo
            if submode == 'queue':
                subpro = subprocess.call(cmdinfo.encode(sys.getfilesystemencoding()), shell = True)
            elif submode == 'batch':
                subpro = subprocess.Popen(cmdinfo.encode(sys.getfilesystemencoding()), shell = True)
            elif submode == 'batchmsg':
                subpro = subprocess.Popen(cmdinfo.encode(sys.getfilesystemencoding()), shell = True,
                                          stdout = subprocess.PIPE, stderr= subprocess.PIPE)
            if submode in ['batchmsg']:
                msg, err = subpro.communicate()
            #print 'value:  ', msg
            #print 'err:    ', err
        except:
            #print 'system: ', sys.exc_type, sys.exc_info
            pass

        return msg, err