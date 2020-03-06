# $language = "Python"
# $interface = "1.0"

import time
import subprocess

scriptDir = r"C:\Users\bolluak\Automation\Deploy-EE-OCS-config-\deploy_EE_OCS_config.py"
bastian_hostname = "NBN_NOC_Bastion_SAM_2FA_GL"
# Pause script execution in 1000ms or 1 second to allow remote host to time to response
DELAY = 1000


# Network Element secureCRT session class
class ne_crt_session(object):
    NE_CONNECT_STATUS = None  # Track Login status into NE
    ne_crt_session = None

    'network element session'

    def __init__(self, bas_session, hostname, tabname):
        self.ne_host = hostname
        self.Clone_bastian(bas_session, tabname)

    def Clone_bastian(self, bas_session, tabname):
        self.ne_crt_session = bas_session.Clone()
        self.ne_crt_session.Screen.WaitForString("~]$")
        self.ne_crt_session.Screen.Synchronous = True
        self.ne_crt_session.Caption = tabname

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
            data = self.ne_crt_session.Screen.ReadString([waitforstring])
        else:
            crt.Dialog.MessageBox("ERROR: not Login into NE")
        return str(data)


class eas_ocs_configuration(ne_crt_session):
    eas_crt_session = None

    def __init__(self, bastian_session, ne_ip, tab_title):
        self.bastian_session = bastian_session
        self.ne_ip = ne_ip
        self.tab_title = tab_title
        super(eas_ocs_configuration, self).__init__(bastian_session, ne_ip, tab_title)

        self.login()
        Stringdata = self.send_and_retrieve('show port 1/1/1 optical  | match "Serial Number"', "#")
        crt.Dialog.MessageBox(Stringdata, "serial number", IDOK)
        self.logout()
    #def _initiate_eas_session(self):  # Initiate EAS NE session
    #    self.eas_crt_session = ne_crt_session(self.bastian_session, self.ne_ip, self.tab_title)


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


bastian_session = create_bas_session(bastian_hostname, scriptDir)
btd_crt_session = ne_crt_session(bastian_session, "10.227.86.7", "SWBTD0000401")
# crt.Sleep(DELAY)
btd_crt_session.login()
Stringdata = btd_crt_session.send_and_retrieve('show port 1/1/1 optical  | match "Serial Number"', "#")
crt.Dialog.MessageBox(Stringdata, "serial number", IDOK)
btd_crt_session.logout()

eas_config = eas_ocs_configuration(bastian_session, "10.32.3.101", "SWEAS0000121")
# eas_config._initiate_eas_session()
'''#eas_crt_session = ne_crt_session(bastian_session, "10.32.3.101","SWEAS0000121")
#crt.Sleep(DELAY)
eas_crt_session.login()
Stringdata = eas_crt_session.send_and_retrieve('show port 1/1/1 optical  | match "Serial Number"',"#")
crt.Dialog.MessageBox(Stringdata,"serial number", IDOK)
eas_crt_session.logout()
'''
