# $language = "Python"
# $interface = "1.0"

import time
import subprocess
import json
import re
import os
import csv
import os.path
from os import path


scriptDir = r"C:\Users\bolluak\Automation\Deploy-EE-OCS-config-\deploy_EE_OCS_config.py"
main_directory = ''
bastian_hostname = "NBN_NOC_Bastion_SAM_2FA_GL"
# Pause script execution in 1000ms or 1 second to allow remote host to time to response
DELAY = 1000


#network parameters
vpls_id = None
sap_id = None


#------------------------------------------------------------------------------------------------------------
ne_aas_info = {
        'physicalName': None,
        'logicalName': None,
        'port': None,
}

ne_eas_info = {
        'Pri_eas': {'physicalName': None, 'logicalName': None,'lags_id': None},
        'Sec_eas': {'physicalName': None, 'logicalName': None,'lags_id': None},
}

order_paramaters = {

}
#------------------------------------------------------------------------------------------------------------
# Network Element secureCRT session class
class ne_crt_session(object):
    NE_CONNECT_STATUS = None  # Track Login status into NE
    ne_crt_session = None
    session_Tab_Obj = None

    'network element session'

    def __init__(self, bas_session, hostname, tabname):
        self.ne_host = hostname
        self.Clone_bastian(bas_session, tabname)

    def Clone_bastian(self, bas_session, tabname):
        self.ne_crt_session = bas_session.Clone()
        self.ne_crt_session.Screen.WaitForString("~]$")
        self.ne_crt_session.Screen.Synchronous = True
        self.ne_crt_session.Caption = tabname
        self.session_Tab_Obj = crt.GetActiveTab()

    def login(self):
        alulogin_string = "alulogin " + self.ne_host  # Construct Alulogin string
        self.ne_crt_session.Screen.Send(alulogin_string + "\n")
        if self.ne_crt_session.Screen.WaitForString("Welcome"):
            self.NE_CONNECT_STATUS = True
            crt.Sleep(DELAY)
        else:
            self.NE_CONNECT_STATUS = False

    def login_serial(self):  # Custom Function to Handle Serial Connection
        self.ne_crt_session.Screen.Send("\n")
        if self.ne_crt_session.Screen.WaitForString("A:SWBTD0000034#"):
            self.NE_CONNECT_STATUS = True
        else:
            self.NE_CONNECT_STATUS = False

    def logout(self):
        if (self.NE_CONNECT_STATUS == True):
            self.ne_crt_session.Screen.Send("logout" + "\n")
            self.ne_crt_session.Screen.WaitForString("~]$")
            self.NE_CONNECT_STATUS = False
        else:
            crt.Dialog.MessageBox("ERROR: not Login into NE")

    def send_command(self, command):
        if (self.NE_CONNECT_STATUS == True):
            self.ne_crt_session.Screen.Send(command + "\n")
            self.ne_crt_session.Screen.WaitForStrings(['A:SW','*A:SW','B:SW','*B:SW'])
        else:
            crt.Dialog.MessageBox("ERROR: not Login into NE")

    def send_and_retrieve(self, command, waitforstring):
        data = " "
        if (self.NE_CONNECT_STATUS == True):
            self.ne_crt_session.Screen.Send(command + "\n")
            self.ne_crt_session.Screen.WaitForString(command)
            data = self.ne_crt_session.Screen.ReadString(['A:' + waitforstring,'*A:' + waitforstring,
                                                          'B:' + waitforstring,'*B:' + waitforstring])
        else:
            crt.Dialog.MessageBox("ERROR: not Login into NE")
        return str(data)

#------------------------------------------------------------------------------------------------------------
class eas_ocs_configuration(ne_crt_session):
    def __init__(self, bastian_session, eas_type, ne_host, tab_title):
        self.bastian_session = bastian_session
        self.ne_host = ne_host
        self.tab_title = tab_title
        self.eas_type = eas_type
        super(eas_ocs_configuration, self).__init__(bastian_session, ne_host, tab_title)


    def check_vpls_and_sap(self):
        self.session_Tab_Obj.Activate()
        self.login()

        vpls_id = self.vpls_exist()
        if vpls_id and (len(vpls_id) == 8):
            if not self.sap_exist(vpls_id):
                crt.Dialog.MessageBox("VPLS exist and SAP missing,  call deploy Ocs")
                self.deploy_ocs_config()
        self.logout()


    def vpls_exist(self):
        vpls_check = self.send_and_retrieve('show service service-using vpls customer 10 | match  "OCS for BNTD Management"', "SW")

        'if vpls does not exist'
        if not vpls_check.strip():
            ' Investigate why vpls missing'
            crt.Dialog.MessageBox("Vpls does not exist In network, Investigate why vpls missing, exiting script","Missing VPLS", IDOK)
            crt.Quit()
            return False

        else:
            vpls_id = vpls_check.split()[0]
            crt.Dialog.MessageBox(str(vpls_id), "vpls id:", IDOK)

            'if vpls exist, validate its format: '
            if(re.match(str("^2000") + str(ne_eas_info[self.eas_type]['physicalName'][0]) +'4' + str("\d\d$"),str(vpls_id))):
                 return vpls_id


    def sap_exist(self,vpls_id):
        sap_check = self.send_and_retrieve('show service id ' + str(vpls_id) + ' base | match sap:lag-'
                                           + str(ne_eas_info[self.eas_type]['lags_id']), "SW")
        if not sap_check.strip():
            return False
        else:
            sap_id = sap_check.split()[0]  # split line into list along white space
            crt.Dialog.MessageBox(str(sap_id), "Sap existed in EAN network: sap id is:", IDOK)
            return True



    def deploy_ocs_config(self):
        with open(main_directory + r"\\" + str(order_paramaters['Appian Order']) + '-' + str(order_paramaters['BNTD Logical Device name']) + "-ocs_config.txt",'r') as text_file:
             OCS_config = text_file.read().splitlines()
             EAS_OCS_Config = []
             for line in OCS_config:
                 if (ne_eas_info[self.eas_type]['physicalName'] in line):

                     EAS_OCS_Config.append(OCS_config[OCS_config.index(line):OCS_config.index(line) + 44])

                     EAS_OCS_Config = EAS_OCS_Config[0]

                     crt.Dialog.MessageBox(str(EAS_OCS_Config), "EAS OCS Config are",IDOK)

                     'send config line by line to eas box'
                     for line in EAS_OCS_Config:
                        self.send_command(line)
                        #crt.Dialog.MessageBox("continue send config ?")
                     break



#------------------------------------------------------------------------------------------------------------
class aas_ocs_configuration(ne_crt_session):
    aas_crt_session = None

    def __init__(self, bastian_session, ne_host, tab_title):
        self.bastian_session = bastian_session
        self.ne_host = ne_host
        self.tab_title = tab_title
        super(aas_ocs_configuration, self).__init__(bastian_session, ne_host, tab_title)

    def check_vpls_and_sap(self):
        self.login()
        vpls_check = self.send_and_retrieve('show service service-using vpls customer 10 | match  "OCS for BNTD Management"', "SW")

        'IF Vpls is missing in AAS or else deploy aas port config'
        if not vpls_check.strip():

            ' Deploy Ocs config'
            self.deploy_ocs_config()
            'Deploy aas config'
            if not(self.sap_exist(vpls_check.split()[0])):
                self.deploy_aas_config()

        else:

            'Deploy aas config'
            if not(self.sap_exist(vpls_check.split()[0])):
                self.deploy_aas_config()

        self.check_aas_sfp()

        self.logout()

    def deploy_ocs_config(self):
        with open(main_directory + r"\\" + str(order_paramaters['Appian Order']) + '-' + str(order_paramaters['BNTD Logical Device name']) + "-ocs_config.txt",'r') as text_file:
             OCS_config = text_file.read().splitlines()
             AAS_OCS_Config = []
             for line in OCS_config:
                 if (ne_aas_info['physicalName'] in line):
                     AAS_OCS_Config.append(OCS_config[OCS_config.index(line):OCS_config.index(line) + 63])

                     AAS_OCS_Config = AAS_OCS_Config[0]

                     crt.Dialog.MessageBox(str(AAS_OCS_Config), "AAS OCS Config are",IDOK)

                     'send config line by line to aas box'
                     for line in AAS_OCS_Config:
                        self.send_command(line)
                        #crt.Dialog.MessageBox("continue send config ?")
                     break


    def deploy_aas_config(self):
        if (not self.is_mac_filter_config() and
           (not self.is_aas_lag_config()) and
           (not self.is_aas_port_config())):

            crt.Dialog.MessageBox("port ,Mac Filter and lag not configured")
            with open(main_directory + r"\\" + str(order_paramaters['Appian Order']) + '-' + str(order_paramaters['AAS Logical Name']) +
                      '-' + str(order_paramaters['BNTD Logical Device name']) + "-aas_config.txt", 'r') as text_file:


                 aas_config  = text_file.read().splitlines()
                 for line in aas_config:
                     self.send_command(line)
                     #crt.Dialog.MessageBox("continue send config ?")


    def is_mac_filter_config(self):
        "check mac filter configuration"

        mac_filter = self.send_and_retrieve("show filter  mac | match expression " + '"' +
                                            order_paramaters['AAS UNIQUE MAC Filter for BNTD'] + '|' +
                                            order_paramaters['BNTD Logical Device name'] +'"', "SW")
        if not mac_filter.strip():
            status = False
        else:
            status = True
        return status


    def is_aas_port_config(self):
        "check port configuration"

        self.send_command("/configure port " + str(ne_aas_info['port']).replace(" ",""))
        port_config_s = self.send_and_retrieve("info", str(ne_aas_info['logicalName']).replace(" ","") + ">config>port#")
        self.send_command('exit all')
        port_config_l = port_config_s.splitlines()

        #if (port_config_l[2].replace(" ","") == "shutdown" and port_config_l[3].replace(" ", "") == "ethernet" and port_config_l[4].replace(" ", "") == "exit"):
        if (port_config_l[2].strip() == "shutdown" and
            port_config_l[3].strip() == "ethernet" and
            port_config_l[4].strip() == "exit"):

            status = False

        else:
            status = True

        return status



    def is_aas_lag_config(self):

        "check_lag_config"
        lag_config_s =  self.send_and_retrieve('show lag '+ order_paramaters['AAS to BTD LAG ID (Downstream LAG to BNTD)'] +
                                               ' | match ' + '"No Entries Found"',str(ne_aas_info['logicalName']).replace(" ","")+"#")
        if lag_config_s.strip() == "No Entries Found":
             status = False
        else:
            status = True
        return status


    def sap_exist(self,vpls_id):
        sap_check = self.send_and_retrieve('show service id ' + str(vpls_id) + ' base | match sap:lag-'
                                           + str(order_paramaters['AAS to BTD LAG ID (Downstream LAG to BNTD)']), "SW")
        if not sap_check.strip():
            return False
        else:
            sap_id = sap_check.split()[0]  # split line into list along white space
            crt.Dialog.MessageBox(str(sap_id), "Sap existed in AAS network: sap id is:", IDOK)
            return True

    def check_aas_sfp(self):
        Optical_Compliance = self.send_and_retrieve('show port ' + str(ne_aas_info['port']).replace(" ","") +
                                                    ' optical | match "Optical Compliance"',str(ne_aas_info['logicalName']).replace(" ","")+"#")
        Link_Length_support = self.send_and_retrieve('show port ' + str(ne_aas_info['port']).replace(" ","") +
                                                    ' optical | match "Link Length support"',str(ne_aas_info['logicalName']).replace(" ","")+"#")

        check_sfp = lambda x: True  if(x[0:1] in Optical_Compliance) and (x[2:3] in Link_Length_support) else False
        if check_sfp(order_paramaters['AAS SFP Type']):
            #crt.Dialog.MessageBox(Optical_Compliance+'   SFP  ' + Link_Length_support + '    '  ,"SFP in AAS DOES MATCH design")
        else:
            crt.Dialog.MessageBox(Optical_Compliance + '   SFP  ' + Link_Length_support + '    ',"SFP in AAS DOES NOT MATCH design, Please Notify PM")

#------------------------------------------------------------------------------------------------------------

#------------------------------------------------------------------------------------------------------------
def create_bas_session(remote_Machine, script):
    """
    :param remote_Machine:      hostname
    :param script:              Script to run(load) Into SecureCRT Environment
    :return:                    Return Session Objects
    """
    global session
    if __name__ == '__main__':
        subprocess.call([
            "C:/Program Files/VanDyke Software/SecureCRT/SecureCRT.exe",
            "/SCRIPT", script
        ])

    else:
        session = crt.Session.ConnectInTab("/s " + remote_Machine, True, True)
        session.Screen.Synchronous = True
        session.Screen.IgnoreEscape = True
        session.Screen.WaitForString("~]$")
    return session



#------------------------------------------------------------------------------------------------------------
def pni_trace_data(ee_directory):
    with open(ee_directory + '\PNI Trace.json',"r") as read_json:
        data = json.load(read_json)


        #AAS Information
        ne_aas_info['physicalName'] = data['aas']['physicalName']
        ne_aas_info['logicalName'] = data['aas']['logicalName']
        ne_aas_info['port'] = data['aas']['port']

        #EAS information
        eas_devices = data['device']

        # EAs Primary info
        ne_eas_info['Pri_eas']['physicalName'] = eas_devices[0]["physicalName"]
        ne_eas_info['Pri_eas']['logicalName'] = eas_devices[0]["logicalName"]
        ne_eas_info['Pri_eas']['lags_id'] = eas_devices[0]['lags']['lagIdA']

        # EAs Secondary info
        ne_eas_info['Sec_eas']['physicalName'] = eas_devices[1]["physicalName"]
        ne_eas_info['Sec_eas']['logicalName'] = eas_devices[1]["logicalName"]
        ne_eas_info['Sec_eas']['lags_id'] = eas_devices[1]['lags']['lagIdA']


#------------------------------------------------------------------------------------------------------------
def config_directory(main_directory):
    _btd_logical_name = [x for x in main_directory.split() if re.search("SWBTD",x)]
    conf_dir_path = [x for x in os.listdir(main_directory) if re.search(str(_btd_logical_name[0] + "-Connect-Config"),x)]
    return conf_dir_path[0][0:42]

#------------------------------------------------------------------------------------------------------------
def load_order_paramaters (main_directory, key):
     f_name  = [x for x in os.listdir(main_directory) if re.search("-parameters.csv",x)]
     with open(main_directory + r"\\" + f_name[0], 'r') as csv_file:
          csv_reader_obj = csv.reader(csv_file)
          for row in csv_reader_obj:
              k,v = row
              order_paramaters[k] = v
     return order_paramaters[key]

#------------------------------------------------------------------------------------------------------------

def get_directory():
    directory_path = crt.Dialog.Prompt("Enter Files Directory", "DIRECTORY", "", False)
    try:
        if (not path.exists(directory_path)):
            raise ValueError('path not valid')
    except (ValueError, IndexError):
        while(not path.exists(directory_path)):
            directory_path = crt.Dialog.Prompt("Enter Files Directory", "Wrong Directory, Please Try Again", "", False)

    return directory_path
#------------------------------------------------------------------------------------------------------------

bastian_session = create_bas_session(bastian_hostname, scriptDir)

main_directory = str(get_directory())

pni_trace_data(main_directory)
load_order_paramaters(main_directory, 'Appian Order')





pri_eas_config = eas_ocs_configuration(bastian_session, 'Pri_eas', ne_eas_info['Pri_eas']['logicalName'], ne_eas_info['Pri_eas']['logicalName'])
sec_eas_config = eas_ocs_configuration(bastian_session, 'Sec_eas', ne_eas_info['Sec_eas']['logicalName'], ne_eas_info['Sec_eas']['logicalName'])

pri_eas_config.check_vpls_and_sap()
sec_eas_config.check_vpls_and_sap()

aas_config = aas_ocs_configuration(bastian_session, ne_aas_info['logicalName'],  ne_aas_info['logicalName'])
aas_config.check_vpls_and_sap()



''' 
btd_crt_session = ne_crt_session(bastian_session, "10.227.86.7", "SWBTD0000401")
# crt.Sleep(DELAY)
btd_crt_session.login()
Stringdata = btd_crt_session.send_and_retrieve('show port 1/1/1 optical  | match "Serial Number"', "SW")
btd_crt_session.logout()

crt.Dialog.MessageBox(str(ne_aas_info), "AAS Info", IDOK)
crt.Dialog.MessageBox(str(ne_eas_info), "EAS's  Info", IDOK)
'''
