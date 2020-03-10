# $language = "Python"
# $interface = "1.0"

import time
import subprocess
import json
import re
import os
import csv


scriptDir = r"C:\Users\bolluak\Automation\Deploy-EE-OCS-config-\deploy_EE_OCS_config.py"
main_directory = r"S:\Infrastructure Integration\EE\EE Completed orders\03-VIC\3HGT-70-556-BTD-0601 SWBTD0000555 for SANDRINGHAM SECONDARY COLLEGE ROR000000025631\SWBTD0000555-Connect-Config-20200305_09_34"
bastian_hostname = "NBN_NOC_Bastion_SAM_2FA_GL"
# Pause script execution in 1000ms or 1 second to allow remote host to time to response
DELAY = 1000


#network parameters
vpls_id = None
sap_id =  None

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
            self.ne_crt_session.Screen.WaitForString('\r\n')
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
        self.session_Tab_Obj.Activate()                                                                                 #Bring session tab foreground
        self.login()

        vpls_check = self.send_and_retrieve('show service service-using vpls customer 10 | match  "OCS for BNTD Management"', "SW")

        if not vpls_check.strip():                                                             # If return string is emptry
            crt.Dialog.MessageBox("Vpls does not exist In network","Missing VPLS", IDOK)
            ' Investigate why configuration missing'
        else:
            vpls_id = vpls_check.split()[0]                                                     #split line into list along white space
            crt.Dialog.MessageBox(str(vpls_id), "vpls id:", IDOK)

            sap_check = self.send_and_retrieve('show service id ' + str(vpls_id) + ' base | match sap:lag-'
                                               + str(ne_eas_info[self.eas_type]['lags_id']), "SW")

            if not sap_check.strip():                                                            #if sap is missing and not configured in VPLS
                " Configured sap, it's missing "
                crt.Dialog.MessageBox("Sap missing, configured", "missing sap id:", IDOK)

                " More actions to configure sap into vpls"
                self.deploy_ocs_config()
            else:
                sap_id = sap_check.split()[0]  # split line into list along white space
                crt.Dialog.MessageBox(str(sap_id), "Sap existed in EAN network: sap id is:", IDOK)

                self.deploy_ocs_config()

        self.logout()

    def deploy_ocs_config(self):
        ROR_order_id = order_paramater_value(main_directory, 'Appian Order')
        btd_logical_name = order_paramater_value(main_directory, 'BNTD Logical Device name')

        with open(main_directory + r"\\" + str(ROR_order_id) + '-' + str(btd_logical_name) + "-ocs_config.txt",'r') as text_file:
             OCS_config = text_file.read().splitlines()
             EAS_OCS_Config = []

             for line in OCS_config:
                 if ne_eas_info[self.eas_type]['physicalName'] in line:
                    EAS_OCS_Config.append(OCS_config[OCS_config.index(line):OCS_config.index(line) + 44])
                    crt.Dialog.MessageBox(str(EAS_OCS_Config), "EAS OCS Config are",IDOK)
                    break



#------------------------------------------------------------------------------------------------------------
class aas_ocs_configuration(ne_crt_session):
    aas_crt_session = None

    def __init__(self, bastian_session, ne_host, tab_title):
        self.bastian_session = bastian_session
        self.ne_host = ne_host
        self.tab_title = tab_title
        super(aas_ocs_configuration, self).__init__(bastian_session, ne_host, tab_title)


        self.login()
        Stringdata = self.send_and_retrieve('show port 1/1/1 optical  | match "Serial Number"', "SW")
        crt.Dialog.MessageBox(Stringdata, "serial number", IDOK)
        self.logout()
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

        # EAs Primary info
        ne_eas_info['Sec_eas']['physicalName'] = eas_devices[1]["physicalName"]
        ne_eas_info['Sec_eas']['logicalName'] = eas_devices[1]["logicalName"]
        ne_eas_info['Sec_eas']['lags_id'] = eas_devices[1]['lags']['lagIdA']



def config_directory(main_directory):
    _btd_logical_name = [x for x in main_directory.split() if re.search("SWBTD",x)]
    conf_dir_path = [x for x in os.listdir(main_directory) if re.search(str(_btd_logical_name[0] + "-Connect-Config"),x)]
    return conf_dir_path[0][0:42]


def order_paramater_value (main_directory,key):
     f_name  = [x for x in os.listdir(main_directory) if re.search("-parameters.csv",x)]
     with open(main_directory + r"\\" + f_name[0], 'r') as csv_file:
          csv_reader_obj = csv.reader(csv_file)
          for row in csv_reader_obj:
              k,v = row
              order_paramaters[k] = v
     return order_paramaters[key]


pni_trace_data(main_directory)

bastian_session = create_bas_session(bastian_hostname, scriptDir)

pri_eas_config = eas_ocs_configuration(bastian_session, 'Pri_eas', ne_eas_info['Pri_eas']['logicalName'], ne_eas_info['Pri_eas']['logicalName'])
sec_eas_config = eas_ocs_configuration(bastian_session, 'Sec_eas', ne_eas_info['Sec_eas']['logicalName'], ne_eas_info['Sec_eas']['logicalName'])
aas_config = aas_ocs_configuration(bastian_session, ne_aas_info['logicalName'],  ne_aas_info['logicalName'])

pri_eas_config.check_vpls_and_sap()
sec_eas_config.check_vpls_and_sap()

btd_crt_session = ne_crt_session(bastian_session, "10.227.86.7", "SWBTD0000401")
# crt.Sleep(DELAY)
btd_crt_session.login()
Stringdata = btd_crt_session.send_and_retrieve('show port 1/1/1 optical  | match "Serial Number"', "SW")
btd_crt_session.logout()

crt.Dialog.MessageBox(str(ne_aas_info), "serial number", IDOK)
crt.Dialog.MessageBox(str(ne_eas_info), "serial number", IDOK)

