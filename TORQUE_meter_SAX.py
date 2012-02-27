#!/usr/bin/python
# #######################################################################
# TORQUE_meter.py
#
# Parse the status of a site and generate grid accounting records 
# for feeding Gratia 
#
# Ashu Guru 2010/06/10 
#
# #######################################################################

import os
import sys
import time
import subprocess
from string import split,join,count,digits,strip
import datetime
import fcntl
import shutil
from xml.sax import make_parser
from xml.sax.handler import ContentHandler 
import ConfigParser

from gratia.common   import Gratia
from gratia.services import ComputeElement
from gratia.services import ComputeElementRecord

qstat="/opt/torque/bin/qstat"
ProbeConfig = "/etc/gratia/torque-meter/ProbeConfig"
config = ConfigParser.ConfigParser()
config.read( [ "/etc/gratia/torque-meter/meter.conf" ] )


os.environ['TZ'] = 'UTC'
time.tzset()



qstat = config.get("general", "qstat_location")
ce_UniqueID = config.get("general", "ce_unique_id") # "Runtime-Jobs:ff.unl.edu"
ce_CEName = config.get("general", "ce_name") # "ff.unl.edu"
ce_Cluster = config.get("general", "ce_cluster") # "ff.unl.edu"
ce_HostName = config.get("general", "ce_hostname") # "ff-head.unl.edu"
ce_lrmsType = config.get("general" , "lrms_type") # "Torque"
ce_lrmsVersion = config.get("general", "lrms_version") # "Qstat Version - 2.4.8"
ce_CEStateStatus = config.get("general", "ce_state_status") # "Production"


now = datetime.datetime.now()
time_now = time.time()
currdirectory = os.path.realpath(os.path.dirname(__file__))  
Gratia.Initialize(ProbeConfig)
dict_VObased = {}
dict_jobtotals = {'total_running': 0, 'total_queued': 0, 'total_error': 0}
gratia_info = {}


class ParseQstatout(ContentHandler):
    def __init__(self):
        self.elementvalue = ''
        self.j_id = 0
        self.j_owner = ''
        self.j_queue = ''
        self.j_state = ''
        self.j_resources = 1
        self.j_nodes = 0
        self.j_select = 0
        self.j_nodes = ''

    def startElement(self, name, attrs):
    if (name == "Resource_List"):
        pass
    def endElement(self,name):
        if (name == "Job_Id") :
        self.j_id = (self.elementvalue).split('.')[0]
        if (name == "Job_Owner") :
        self.j_owner = (self.elementvalue).split('@')[0]
        if (name == "queue") :
        self.j_queue = (self.elementvalue)
        if (name == "job_state") :
        self.j_state = (self.elementvalue)
        if (name == "select") :
        self.j_select = (self.elementvalue).split(':')[0]
        if (name == "nodes") :
        self.j_nodes = (self.elementvalue)
        if (name == "nodect") :
        self.j_nodect = (self.elementvalue)
    if (name == "Resource_List"):
        if(self.j_select > 0):
        self.j_resources = int(self.j_select)
            else:
                j_nodesSpec = self.j_nodes.split(':')
                j_nodect = 1
                j_nodeppn = 1
                if len(j_nodesSpec) > 1:
                    j_nodect = j_nodesSpec[0]
                    j_nodeppn = 0
                    try:
                        j_nodesSpec[1].index('ppn=')
                        j_nodeppn = j_nodesSpec[1].replace('ppn=', '')
                    except ValueError:
                        pass
                else:
            try:
                        j_nodeppn = 1
                        j_nodect = int(j_nodesSpec[0])
            except:
                            pass

            try:
                self.j_resources = int(j_nodect) * int(j_nodeppn)
            except:
                self.j_resources = len(self.j_nodes.split(',')) * int(j_nodeppn)


    if (name == "Job") :
            if not dict_VObased.has_key(self.j_owner):
                dict_VObased[self.j_owner]={'VO':self.j_owner}

            if self.j_state == 'R' and not (dict_VObased[self.j_owner]).has_key('RunningCores'):
                 dict_VObased[self.j_owner]['RunningCores']=self.j_resources
             dict_jobtotals['total_running'] = int(dict_jobtotals['total_running'])+int(self.j_resources)
            elif self.j_state == 'R':
                 dict_VObased[self.j_owner]['RunningCores']=dict_VObased[self.j_owner]['RunningCores']+int(self.j_resources)
                 dict_jobtotals['total_running'] = int(dict_jobtotals['total_running'])+int(self.j_resources)

            elif self.j_state == 'Q' and not (dict_VObased[self.j_owner]).has_key('QueuedCores'):
                 dict_VObased[self.j_owner]['QueuedCores']=self.j_resources
             dict_jobtotals['total_queued'] = int(dict_jobtotals['total_queued'])+int(self.j_resources)
            elif self.j_state == 'Q':
                 dict_VObased[self.j_owner]['QueuedCores']=dict_VObased[self.j_owner]['QueuedCores']+int(self.j_resources)
                 dict_jobtotals['total_queued'] = int(dict_jobtotals['total_queued'])+int(self.j_resources)

            elif self.j_state == 'E' and not (dict_VObased[self.j_owner]).has_key('ErrorCores'):
                 dict_VObased[self.j_owner]['ErrorCores']=self.j_resources
             dict_jobtotals['total_error'] = int(dict_jobtotals['total_error'])+int(self.j_resources)
            elif self.j_state == 'E':
                 dict_VObased[self.j_owner]['ErrorCores']=dict_VObased[self.j_owner]['ErrorCores']+int(self.j_resources)
                 dict_jobtotals['total_error'] = int(dict_jobtotals['total_error'])+int(self.j_resources)


            self.j_id = 0
            self.j_owner = ''
            self.j_queue = ''
            self.j_state = ''
            self.j_resources = int(1)
            self.j_nodes = 0
            self.j_select = 0
            self.j_nodes = ''

    self.elementvalue=''
    def characters(self, chars):
    self.elementvalue += chars


# #######################################################################
# Methods started
# #######################################################################
def parseQstatOutputAndSend():

    if not qstat:
        print "PBS: qstat cmd is not in our path, exiting."
        sys.exit (1)
     

    qstatxml = open(currdirectory+'/'+'QSTATOUT.xml', 'w')
    p = subprocess.Popen("%s -x -t"% (qstat), stdout=qstatxml, stderr=qstatxml, shell=True, close_fds=True)
    p.wait()
    qstatxml.close()

    qstatresult = ParseQstatout()
    saxparser = make_parser()
    saxparser.setContentHandler(qstatresult)

    datasource = open(currdirectory+'/'+"QSTATOUT.xml","r")
    saxparser.parse(datasource)
    #move the directory
    shutil.move(currdirectory+'/'+"QSTATOUT.xml", currdirectory+'/'+"QSTATOUT.1.xml")

    #for debugging 
    sendDataCE=1;
    sendDataCER=1;
    #----------------------------------------------------
    #Send the ComputeElement Here
    #----------------------------------------------------
    total_running=total_queued= total_error=0         
    if(sendDataCE > 0):
        Gratia.Initialize(ProbeConfig)
        
        ce_MaxRunningJobs = total_running  
        ce_maxTotalJobs = total_running + total_queued
        ce_assignedJobSlots = total_running + total_queued
        
        ce = ComputeElement.ComputeElement()
        ce.UniqueID(ce_UniqueID)
        ce.CEName(ce_CEName)
        ce.Cluster(ce_Cluster)
        ce.HostName(ce_HostName)
        ce.Timestamp(time_now)
        ce.LrmsType(ce_lrmsType)
        ce.LrmsVersion(ce_lrmsVersion)
        ce.MaxRunningJobs(ce_MaxRunningJobs)
        ce.MaxTotalJobs(ce_maxTotalJobs)
        ce.AssignedJobSlots(ce_assignedJobSlots)
        ce.Status(ce_CEStateStatus)
        Gratia.Send(ce)

    print 'TotalRunningCores: %d : TotalQueuedCores: %d : TotalErrorCores: %d ' % (dict_jobtotals['total_running'],dict_jobtotals['total_queued'],dict_jobtotals['total_error'])
    total_running=total_queued= total_error=0         
    for mkey in dict_VObased:
        queuedCores=runningCores=errorCores=0
        if((dict_VObased[mkey]).has_key('RunningCores')):
            runningCores=dict_VObased[mkey]['RunningCores']
            total_running=total_running+runningCores
        if((dict_VObased[mkey]).has_key('QueuedCores')):
            queuedCores=dict_VObased[mkey]['QueuedCores']
            total_queued=total_queued+queuedCores
        if((dict_VObased[mkey]).has_key('ErrorCores')):
            errorCores=dict_VObased[mkey]['ErrorCores']
            total_error=total_error+errorCores
        print 'VO: %s : RunningCores: %d : QueuedCores: %d : ErrorCores: %d ' % (mkey,runningCores,queuedCores,errorCores)
        
        if(sendDataCER > 0):
            VO= mkey
            runningCores= runningCores
            queuedCores= queuedCores
            errorCores= errorCores
            cer = ComputeElementRecord.ComputeElementRecord()
            cer.UniqueID(ce_UniqueID)
            cer.VO(VO)
            cer.Timestamp(str(now) + "Z")
            cer.RunningJobs(runningCores)
            cer.TotalJobs(runningCores)#not sure about the diff between the param above
            cer.WaitingJobs(queuedCores)
            Gratia.Send(cer)
            
    print 'TotalRunningCores: %d : TotalQueuedCores: %d : TotalErrorCores: %d ' % (total_running,total_queued,total_error)
               
                
  
    
def which(program):
    import os
    def is_exe(fpath):
        return os.path.exists(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file
    return None

def testdatasend():
    Gratia.Initialize(ProbeConfig)
    
    ce_MaxRunningJobs = 25  # REPLACE THESE WITH ACTUAL NUMBERS
    ce_maxTotalJobs = 20
    ce_assignedJobSlots = 20
    
    ce = ComputeElement.ComputeElement()
    ce.UniqueID(ce_UniqueID)
    ce.CEName(ce_CEName)
    ce.Cluster(ce_Cluster)
    ce.HostName(ce_HostName)
    ce.Timestamp(time_now)
    ce.LrmsType(ce_lrmsType)
    ce.LrmsVersion(ce_lrmsVersion)
    ce.MaxRunningJobs(ce_MaxRunningJobs)
    ce.MaxTotalJobs(ce_maxTotalJobs)
    ce.AssignedJobSlots(ce_assignedJobSlots)
    ce.Status(ce_CEStateStatus)
    Gratia.Send(ce)
    for line in open('TESTDATA.txt','r').readlines(): #for time being just read a text file for debugging
        spltstr=line.split(':')
        VO= spltstr[1]
        runningCores= spltstr[3].strip()
        queuedCores= spltstr[5].strip()
        errorCores= spltstr[7].strip()
        cer = ComputeElementRecord.ComputeElementRecord()
        cer.UniqueID(ce_UniqueID)
        cer.VO(VO)
        cer.Timestamp(str(now) + "Z")
        cer.RunningJobs(runningCores)
        cer.TotalJobs(runningCores)
        cer.WaitingJobs(queuedCores)
        Gratia.Send(cer)
 


def main(*args):
    pid_file = os.path.realpath(os.path.dirname(__file__))+'/program.pid'
    
    fp = open(pid_file, 'w')
    try:
        fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        print "Exiting since another instance running"
        sys.exit(0)

    parseQstatOutputAndSend() 
    #testdatasend()
     
if __name__ == '__main__':
    sys.exit(main(*sys.argv)) 

