# File Open Dialog
import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QPushButton, QScrollArea, QVBoxLayout, QCheckBox, QInputDialog, QLineEdit, QComboBox, QMessageBox, QWidget, QDialog
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtWidgets import QTableWidget,QTableWidgetItem, QLabel
from PyQt5.QtGui import QPixmap, QIcon
import omero
from omero.gateway import BlitzGateway
import subprocess
sys.path.append("/Users/alexrapp/Dev/OMERO.server-5.6.1-ice36-b225/lib")
import ntpath
import os
import platform
import paramiko
import tempfile						# for local temp file generation
import time
import pickle


LastStateRole = QtCore.Qt.UserRole

global tempdir
tempdir = '/tmp' if platform.system() == 'Darwin' else tempfile.gettempdir()

class Ui_TestQFileDialog(object):
    def createFileTable(self, fileList):
        self.fileTable = QTableWidget()
        self.fileTable.setRowCount(len(fileList))
        self.fileTable.setColumnCount(4)
        self.fileTable.setHorizontalHeaderLabels(['Include', 'Target','Name', 'Path'])
        for l in range (len(fileList)):
            item = QtWidgets.QTableWidgetItem()
            item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            item.setCheckState(QtCore.Qt.Checked)
            item.setData(LastStateRole, item.checkState())
            self.fileTable.setItem(l,0,item)
            self.fileTable.setItem(l,1,QTableWidgetItem(""))
            nameString = ntpath.basename(fileList[l])
            self.fileTable.setItem(l,2,QTableWidgetItem(nameString))
            self.fileTable.setItem(l,3,QTableWidgetItem(fileList[l]))
        self.fileTable.setColumnWidth(0,40)
        self.fileTable.setColumnWidth(0,80)    
        self.layout = QVBoxLayout(self.scrollArea)
        self.layout.addWidget(self.fileTable)

    def buildIPIfileList(self):
        global fileList
        newFileList = []
        lMount = self.localMount.text()
        rMount = self.remoteMount.text()
        temp_tsv = open(tempdir + os.sep + "temp.tsv", "w") 				# encoding='utf-8'?
        print(fileList)
        for row in range (len(fileList)):
            if self.fileTable.item(row,0).checkState() == QtCore.Qt.Checked:
            #if self.fileTable.cellWidget(row,0).isChecked:
                string = fileList[row]
                print(string)
                string2 = string.replace(lMount, rMount, 1)
                print(string2)
                importLine = 'Dataset:name:'+self.fileTable.item(row,1).text()+'\t'+self.fileTable.item(row,2).text()+'\t'+string2
                print(importLine)
                temp_tsv.write(importLine + '\n')
        temp_tsv.close()
        ## write the YAML file
        yamlFile = open(tempdir + os.sep + "temp.yml", "w") #, encoding='utf-8'
        yamlFile.write("---\n")
        yamlFile.write("continue: \"true\"\n")
        yamlFile.write("transfer: \"ln_s\"\n")
        yamlFile.write("checksum_algorithm: \"File-Size-64\"\n")
        yamlFile.write("logprefix: \"logs/\"\n")
        yamlFile.write("output: \"yaml\"\n")
        yamlFile.write("path: \"/OMERO/ManagedRepository/ipimp.tsv\"\n")
        yamlFile.write("columns:\n")
        yamlFile.write("   - target\n") # use three blanks, no tab!
        yamlFile.write("   - name\n")
        yamlFile.write("   - path\n")
        yamlFile.close()

    def _open_file_dialog(self):
        # clear existing file tables                                     ## TODO
        directory = str(QtWidgets.QFileDialog.getExistingDirectory())
        self.importPath.setText('{}'.format(directory))
        print(directory)
        fDepth = self.folderDepth.currentText()
        print(fDepth)
        if fDepth == ">3":
            fDepth = "7"
        print(fDepth)
        scanString = 'omero import -f --depth ' +fDepth+ ' \''+ directory+'\''
        proc=subprocess.Popen(scanString, shell=True, stdout=subprocess.PIPE, universal_newlines=True)
        output=proc.communicate()[0]
        print(output)
        global fileList
        fileList = []
        for line in output.splitlines():
            if not line.startswith('#'):
                print(line)
                fileList.append(line)
        self.createFileTable(fileList)

    def startOmeroImport(self):
        print('Clicked Pyqt button.')
        inplaceUserField = self.inplaceUser.text()
        inplacePassField = self.inplacePW.text()
        serverField = self.OServer.text()
        targetUserField = self.TargetUser.text()
        importString = "omero import --sudo "+ inplaceUserField + " -w " + inplacePassField+ " -s \"" + serverField + "\" -u " + targetUserField + " --bulk /OMERO/ManagedRepository/bulki.yml"
        print(importString)
        # open the ssh and transfer the bulk and yaml files
        source1 = tempdir + os.sep +"temp.tsv"
        dest1 = "/OMERO/ManagedRepository/ipimp.tsv"
        source2 = tempdir + os.sep +"temp.yml"
        dest2 = "/OMERO/ManagedRepository/bulki.yml"
        try:
            t = paramiko.Transport((serverField))
            t.connect(username=inplaceUserField, password=inplacePassField)
            sftp = paramiko.SFTPClient.from_transport(t)
            # upload the tsv file
            sftp.put(source1, dest1, callback=None, confirm=True)
            # upload the yml file
            sftp.put(source2, dest2, callback=None, confirm=True)
        finally:
            t.close()
            print("bulk uploaded")
        #### issue the import command
        try:
            client = paramiko.SSHClient()
            client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.set_missing_host_key_policy(paramiko.WarningPolicy)
            client.connect(hostname=serverField, username=inplaceUserField, password=inplacePassField)
            stdin, stdout, stderr = client.exec_command("mkdir /OMERO/ManagedRepository/i_did_it")
            stdin, stdout, stderr = client.exec_command("omero import --sudo "+ inplaceUserField + " -w " + inplacePassField + " -s "+ serverField + " -u " + targetUserField + " --bulk /OMERO/ManagedRepository/bulki.yml")
            stdout.channel.recv_exit_status()
            lines = stdout.readlines()
            print("import done")
            for line in lines:
                print(lines)
        except AuthenticationException:
            print("Authentication failed, please verify your credentials: %s")
        except SSHException as sshException:
            print("Unable to establish SSH connection: %s" % sshException)
        except BadHostKeyException as badHostKeyException:
            print("Unable to verify server's host key: %s" % badHostKeyException)
        finally:
            client.close()
            print("import done")

    def setupUi(self, TestQFileDialog):
        TestQFileDialog.setObjectName("OMERO IPI Tool")
        TestQFileDialog.resize(900, 600)
        
        #### line 1
        self.toolButtonOpenDialog = QtWidgets.QToolButton(TestQFileDialog)
        self.toolButtonOpenDialog.setGeometry(QtCore.QRect(310, 10, 35, 19))
        self.toolButtonOpenDialog.setObjectName("toolButtonOpenDialog")
        self.toolButtonOpenDialog.clicked.connect(self._open_file_dialog)

        self.importPath = QtWidgets.QLineEdit(TestQFileDialog)
        self.importPath.setEnabled(False)
        self.importPath.setGeometry(QtCore.QRect(110, 10, 191, 20))
        self.importPath.setObjectName("importPath")
        
        self.label1 = QtWidgets.QLabel(TestQFileDialog)
        self.label1.setText('Folder to scan')
        self.label1.setGeometry(QtCore.QRect(10,10,90,20))
        self.label1.setObjectName("Label1")
        
        self.label11 = QtWidgets.QLabel(TestQFileDialog)
        self.label11.setText('Scan Depth')
        self.label11.setGeometry(QtCore.QRect(370,10,90,20))
        self.label11.setObjectName("Label11")
        
        self.folderDepth = QComboBox(TestQFileDialog)
        self.folderDepth.addItems(['1','2','3','>3'])
        self.folderDepth.setGeometry(QtCore.QRect(450,8,50,25))
        self.folderDepth.setObjectName("FolderDepth")
        
        logo = QPixmap("Omero_logo.png")
        self.labelImage = QtWidgets.QLabel(TestQFileDialog)
        self.labelImage.setPixmap(logo)
        self.labelImage.setGeometry(QtCore.QRect(560,20,200,50))
        self.label1.setObjectName("Logo")
        
        #### line 2
        self.label2 = QtWidgets.QLabel(TestQFileDialog)
        self.label2.setText('Local mount')
        self.label2.setGeometry(QtCore.QRect(10,50,90,20))
        self.label2.setObjectName("Label2")
        
        self.localMount = QtWidgets.QLineEdit(TestQFileDialog)
        self.localMount.setEnabled(True)
        self.localMount.setGeometry(QtCore.QRect(100, 50, 90, 20))
        self.localMount.setObjectName("localMount")
        
        self.label3 = QtWidgets.QLabel(TestQFileDialog)
        self.label3.setText('Remote mount')
        self.label3.setGeometry(QtCore.QRect(230,50,90,20))
        self.label3.setObjectName("Label3")
        
        self.remoteMount = QtWidgets.QLineEdit(TestQFileDialog)
        self.remoteMount.setEnabled(True)
        self.remoteMount.setGeometry(QtCore.QRect(330, 50, 80, 20))
        self.remoteMount.setObjectName("remoteMount")
        
        self.generateList = QPushButton(TestQFileDialog)
        self.generateList.setStyleSheet('QPushButton {color: black;}')
        self.generateList.setText("Generate List")
        self.generateList.setGeometry(QtCore.QRect(420,50,90,20))
        self.generateList.clicked.connect(self.buildIPIfileList)
        
        #### line 3
        self.scrollArea = QScrollArea(TestQFileDialog)
        self.scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setGeometry(QtCore.QRect(10, 100, 880, 400))
        
        #### line 4
        self.label4 = QtWidgets.QLabel(TestQFileDialog)
        self.label4.setText('Inplace User')
        self.label4.setGeometry(QtCore.QRect(10,520,90,20))
        self.label4.setObjectName("Label4")
        
        self.inplaceUser = QtWidgets.QLineEdit(TestQFileDialog)
        self.inplaceUser.setEnabled(True)
        self.inplaceUser.setGeometry(QtCore.QRect(100, 520, 90, 20))
        self.inplaceUser.setObjectName("inplaceUser")
        
        self.label5 = QtWidgets.QLabel(TestQFileDialog)
        self.label5.setText('Password')
        self.label5.setGeometry(QtCore.QRect(230,520,90,20))
        self.label5.setObjectName("Label5")

        self.inplacePW = QtWidgets.QLineEdit(TestQFileDialog)
        self.inplacePW.setEnabled(True)
        self.inplacePW.setEchoMode(self.inplacePW.Password)
        self.inplacePW.setGeometry(QtCore.QRect(300, 520, 90, 20))
        self.inplacePW.setObjectName("inplacePW")
        
        self.label6 = QtWidgets.QLabel(TestQFileDialog)
        self.label6.setText('Server')
        self.label6.setGeometry(QtCore.QRect(410,520,90,20))
        self.label6.setObjectName("Label6")

        self.OServer = QtWidgets.QLineEdit(TestQFileDialog)
        self.OServer.setEnabled(True)
        self.OServer.setGeometry(QtCore.QRect(460, 520, 110, 20))
        self.OServer.setObjectName("OServer")
        
        self.label7 = QtWidgets.QLabel(TestQFileDialog)
        self.label7.setText('Target User')
        self.label7.setGeometry(QtCore.QRect(590,520,90,20))
        self.label7.setObjectName("Label7")

        self.TargetUser = QtWidgets.QLineEdit(TestQFileDialog)
        self.TargetUser.setEnabled(True)
        self.TargetUser.setGeometry(QtCore.QRect(680, 520, 110, 20))
        self.TargetUser.setObjectName("TargetUser")
        
        #### line 5
        self.label8 =  QtWidgets.QLabel(TestQFileDialog)
        self.label8.setText('Start Import')
        self.label8.setGeometry(QtCore.QRect(10,550,90,20))
        self.label8.setObjectName("Label8")
        
        self.startImport = QPushButton(TestQFileDialog)
        self.startImport.setStyleSheet('QPushButton {color: black;}')
        self.startImport.setText("Start")
        self.startImport.setGeometry(QtCore.QRect(100,550,90,20))
        self.startImport.clicked.connect(self.startOmeroImport)
        
        self.closeAll = QPushButton(TestQFileDialog)
        self.closeAll.setStyleSheet('QPushButton {color: black;}')
        self.closeAll.setText("Quit")
        self.closeAll.setGeometry(QtCore.QRect(240,550,90,20))
        self.closeAll.clicked.connect(app.instance().quit)
        
        self.label10 =  QtWidgets.QLabel(TestQFileDialog)
        self.label10.setText('Server Settings')
        self.label10.setGeometry(QtCore.QRect(590,550,110,20))
        self.label10.setObjectName("Label9")
        
        self.openSettings = QPushButton(TestQFileDialog)
        self.openSettings.setStyleSheet('QPushButton {color: black;}')
        self.openSettings.setText("Settings")
        self.openSettings.setGeometry(QtCore.QRect(700,550,90,20))
        self.openSettings.clicked.connect(self.settingsWindow)
        
        # read settings from stored settings if exist
        if os.path.isfile("ipisettings.p") == 1:
            read_settings = pickle.load( open( "ipisettings.p", "rb" ) )
            print(read_settings)
            self.localMount.setText(read_settings["localMount"])
            self.remoteMount.setText(read_settings["remoteMount"])
            self.inplaceUser.setText(read_settings["inplaceUser"])
            self.inplacePW.setText(read_settings["inplacePass"])
            self.OServer.setText(read_settings["OmeroServer"])
        
        self.retranslateUi(TestQFileDialog)
        QtCore.QMetaObject.connectSlotsByName(TestQFileDialog)

    def retranslateUi(self, TestQFileDialog):
        _translate = QtCore.QCoreApplication.translate
        TestQFileDialog.setWindowTitle(_translate("TestQFileDialog", "OMERO IPI Tool"))
        self.toolButtonOpenDialog.setText(_translate("TestQFileDialog", "..."))

    def settingsWindow(self):
        settingsW = QtWidgets.QDialog()
        settingsW.setModal(True)
        settingsW.setObjectName("OMERO IPI Settings")
        settingsW.resize(400, 300)
        settingsW.setWindowTitle("OMERO Inplace Manager Settings")
        
        settingsLabel0 = QtWidgets.QLabel('Enter the settings for inplace user and Omero server here.', settingsW)
        settingsLabel0.move(10,10)
        
        
        settingsLabel1 = QtWidgets.QLabel("Local Mount",settingsW)
        settingsLabel1.move(20,50)
        
        self.localMountPoint = QtWidgets.QLineEdit(settingsW)
        self.localMountPoint.setEnabled(True)
        self.localMountPoint.setObjectName("localMountPoint")
        self.localMountPoint.setGeometry(QtCore.QRect(140,50,120,20))
        
        
        settingsLabel2 = QtWidgets.QLabel("Remote Mount",settingsW)
        settingsLabel2.move(20,80)
        
        self.remoteMountPoint = QtWidgets.QLineEdit(settingsW)
        self.remoteMountPoint.setEnabled(True)
        self.remoteMountPoint.setObjectName("remoteMountPoint")
        self.remoteMountPoint.setGeometry(QtCore.QRect(140,80,120,20))
        
        
        settingsLabel3 = QtWidgets.QLabel("Inplace User",settingsW)
        settingsLabel3.move(20,110)
        
        self.InplaceU = QtWidgets.QLineEdit(settingsW)
        self.InplaceU.setEnabled(True)
        self.InplaceU.setObjectName("InplaceU")
        self.InplaceU.setGeometry(QtCore.QRect(140,110,120,20))
        
        
        settingsLabel4 = QtWidgets.QLabel("Inplace Password",settingsW)
        settingsLabel4.move(20,140)
        
        self.InplacePass = QtWidgets.QLineEdit(settingsW)
        self.InplacePass.setEnabled(True)
        self.InplacePass.setObjectName("InplacePass")
        self.InplacePass.setEchoMode(self.InplacePass.Password)
        self.InplacePass.setGeometry(QtCore.QRect(140,140,120,20))
        
        
        settingsLabel5 = QtWidgets.QLabel("Omero Server",settingsW)
        settingsLabel5.move(20,170)
        
        self.OmeroServer = QtWidgets.QLineEdit(settingsW)
        self.OmeroServer.setEnabled(True)
        self.OmeroServer.setObjectName("OmeroServer")
        self.OmeroServer.setGeometry(QtCore.QRect(140,170,120,20))
        
        ### Control Buttons
        self.SettingsSave = QPushButton(settingsW)
        self.SettingsSave.setStyleSheet('QPushButton {color: black;}')
        self.SettingsSave.setText("Save")
        self.SettingsSave.setGeometry(QtCore.QRect(50,230,90,20))
        self.SettingsSave.clicked.connect(self.settings_save)
        
        self.SettingsClose = QPushButton(settingsW)
        self.SettingsClose.setStyleSheet('QPushButton {color: black;}')
        self.SettingsClose.setText("Close")
        self.SettingsClose.setGeometry(QtCore.QRect(200,230,90,20))
        #self.SettingsClose.clicked.connect(settingsW.close())
        self.SettingsClose.clicked.connect(settingsW.accept)
        
        settingsW.exec_()

    def settings_save(self):
         lmp = self.localMountPoint.text()
         rmp = self.remoteMountPoint.text()
         ipu = self.InplaceU.text()
         ipp = self.InplacePass.text()
         osname = self.OmeroServer.text()
         ### write the entries back to the main window
         self.localMount.setText(lmp)
         self.remoteMount.setText(rmp)
         self.inplaceUser.setText(ipu)
         self.inplacePW.setText(ipp)
         self.OServer.setText(osname)
         ### compose the pickle dump
         allSettings = {"localMount": lmp, "remoteMount": rmp, "inplaceUser": ipu, "inplacePass": ipp, "OmeroServer": osname}
         pickle.dump( allSettings, open( "ipisettings.p", "wb" ) )
         
        getUserListstring = 'omero user list -s \''+self.localMount.text+'\' -u '+self.inplaceUser.text+' -w '+self.inplacePW.text+
        userproc=subprocess.Popen(getUserListstring, shell=True, stdout=subprocess.PIPE, universal_newlines=True)
        rawUserList=userproc.communicate()[0]
        global userList
        userList = []
        for line in rawUserList.splitlines():
            if not line.startswith('#'):
                print(line)
                fileList.append(line)
    

    
if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(QIcon('IPI_icon.png'))
    TestQFileDialog = QtWidgets.QDialog()
    ui = Ui_TestQFileDialog()
    ui.setupUi(TestQFileDialog)
    TestQFileDialog.show()

    sys.exit(app.exec_())
