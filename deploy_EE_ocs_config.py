# $language = "Python"
# $interface = "1.0"

import time
import subprocess
import json
import re

scriptDir = r"C:\Users\bolluak\Automation\Deploy-EE-OCS-config-\deploy_EE_OCS_config.py"
jsonfile_path = r"S:\Infrastructure Integration\EE\3HGT-70-556-BTD-0601 SWBTD0000555 for SANDRINGHAM SECONDARY COLLEGE ROR000000025631"
bastian_hostname = "NBN_NOC_Bastion_SAM_2FA_GL"
# Pause script execution in 1000ms or 1 second to allow remote host to time to response
DELAY = 1000


#network parameters
vpls_id = None
sap_id =  None

#------------------------------------------------------------------------------------------------------------
ne_aas_info = {
        'physicalName': None,
        'port': None,
}

ne_eas_info = {
        'Pri_eas': {'physicalName': None, 'logicalName': None,'lags_id': None},
        'Sec_eas': {'physicalName': None, 'logicalName': None,'lags_id': None},
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
    def __init__(self, bastian_session, ne_ip, tab_title):
        self.bastian_session = bastian_session
        self.ne_ip = ne_ip
        self.tab_title = tab_title
        super(eas_ocs_configuration, self).__init__(bastian_session, ne_ip, tab_title)


    def check_vpls(self,vplsid):
        self.session_Tab_Obj.Activate()
        self.login()
        vpls_check = self.send_and_retrieve('show service service-using | match  "OCS for BNTD Management"', "SW")
        vpls_id = vpls_check.split()[0]
        crt.Dialog.MessageBox(str(vpls_id), "vpls id:", IDOK)

        sap_check = self.send_and_retrieve('show service id ' + str(vpls_id) + 'base | match sap-' + str(ne_eas_info['Sec_eas']['lags_id']), "SW")
        crt.Dialog.MessageBox(str(sap_check), "sap id:", IDOK)
        self.logout()

#------------------------------------------------------------------------------------------------------------
class aas_ocs_configuration(ne_crt_session):
    aas_crt_session = None

    def __init__(self, bastian_session, ne_ip, tab_title):
        self.bastian_session = bastian_session
        self.ne_ip = ne_ip
        self.tab_title = tab_title
        super(aas_ocs_configuration, self).__init__(bastian_session, ne_ip, tab_title)


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



pni_trace_data(jsonfile_path)

bastian_session = create_bas_session(bastian_hostname, scriptDir)

pri_eas_config = eas_ocs_configuration(bastian_session, ne_eas_info['Pri_eas']['logicalName'], ne_eas_info['Pri_eas']['logicalName'])
sec_eas_config = eas_ocs_configuration(bastian_session, ne_eas_info['Sec_eas']['logicalName'], ne_eas_info['Sec_eas']['logicalName'])
aas_config = aas_ocs_configuration(bastian_session, "10.96.66.16", "SWAAS0000738")

pri_eas_config.check_vpls(vpls_id)
sec_eas_config.check_vpls(vpls_id)

btd_crt_session = ne_crt_session(bastian_session, "10.227.86.7", "SWBTD0000401")
# crt.Sleep(DELAY)
btd_crt_session.login()
Stringdata = btd_crt_session.send_and_retrieve('show port 1/1/1 optical  | match "Serial Number"', "SW")
crt.Dialog.MessageBox(Stringdata, "serial number", IDOK)
btd_crt_session.logout()

crt.Dialog.MessageBox(str(ne_aas_info), "serial number", IDOK)
crt.Dialog.MessageBox(str(ne_eas_info), "serial number", IDOK)
