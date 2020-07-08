#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Alexander Rapp, Technical University Darmstadt, Germany
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import sys
import tempfile
import time
import pickle
import ntpath
import os
import platform
import subprocess
import paramiko
import omero
from random import randint
from omero.gateway import BlitzGateway
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QPushButton, QScrollArea, QVBoxLayout, QCheckBox, QInputDialog, QLineEdit, QComboBox, QMessageBox, QWidget, QDialog
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtWidgets import QTableWidget,QTableWidgetItem, QLabel
from PyQt5.QtGui import QPixmap, QIcon


LastStateRole = QtCore.Qt.UserRole
sessionID = str(randint(10000, 99999))

global tempdir
tempdir = '/tmp' if platform.system() == 'Darwin' else tempfile.gettempdir()
global userList
userList = ['Default']

class Ui_omeroipi(object):
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
        if self.table_place_holder_layout.count():
            self.table_place_holder_layout.takeAt(0).widget().deleteLater()
        self.table_place_holder_layout.addWidget(self.fileTable)

    def toggleChekbox(self):
        times = 1
        self.fileTable = QTableWidget()
        if (times % 2) == 0:
            for l in range (len(fileList)):
                #item = QtWidgets.QTableWidgetItem()
                #item.setCheckState(QtCore.Qt.Unchecked)
                #item.setData(LastStateRole, item.uncheckState())
                #self.fileTable.item(l,0).setChecked(True)
                self.fileTable.item(l,0).setCheckState(True)
                times = times +1
        else:
            for l in range (len(fileList)):
                #item = QtWidgets.QTableWidgetItem()
                #item.setCheckState(QtCore.Qt.Checked)
                #item.setData(LastStateRole, item.checkState())
                #self.fileTable.item(l,0).setChecked(False)
                self.fileTable.item(l,0).setCheckState(False)
                times = times +1

    def showDialog(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText("A User is reqwuired for the import")
        msg.setWindowTitle("Warning")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
        
    def fileListMissing(self):
        flm = QMessageBox()
        flm.setIcon(QMessageBox.Warning)
        flm.setText("You need to generate the filelist befor starting the upload")
        flm.setWindowTitle("Warning")
        flm.setStandardButtons(QMessageBox.Ok)
        flm.exec_()
    def settingsWarning(self):
        setw = QMessageBox()
        setw.setIcon(QMessageBox.Warning)
        setw.setText("No settings file was found, please enter the settings first, save them and restart the App")
        setw.setWindowTitle("Warning")
        setw.setStandardButtons(QMessageBox.Ok)
        setw.exec_()

    def buildIPIfileList(self):
        global fileList
        newFileList = []
        lMount = self.localMount.text()
        rMount = self.remoteMount.text()
        temp_tsv = open(tempdir + os.sep + "ipimp"+sessionID+".tsv", "w")
        # print(fileList)										For debugging only
        for row in range (len(fileList)):
            if self.fileTable.item(row,0).checkState() == QtCore.Qt.Checked:
                string = fileList[row]
                # print(string)											For debugging only
                string2 = string.replace(lMount, rMount, 1)
                # print(string2)										For debugging only
                importLine = 'Dataset:name:'+self.fileTable.item(row,1).text()+'\t'+self.fileTable.item(row,2).text()+'\t'+string2
                # print(importLine)										For debugging only
                temp_tsv.write(importLine + '\n')
        temp_tsv.close()
        ## write the YAML file
        yamlFile = open(tempdir + os.sep + "temp"+sessionID+".yml", "w")
        yamlFile.write("---\n")
        yamlFile.write("continue: \"true\"\n")
        yamlFile.write("transfer: \"ln_s\"\n")
        yamlFile.write("checksum_algorithm: \"File-Size-64\"\n")
        yamlFile.write("logprefix: \"logs/\"\n")
        yamlFile.write("output: \"yaml\"\n")
        yamlFile.write("path: \"/OMERO/ManagedRepository/ipimp"+sessionID+".tsv\"\n")
        yamlFile.write("columns:\n")
        yamlFile.write("   - target\n") # use three blanks, no tab!
        yamlFile.write("   - name\n")
        yamlFile.write("   - path\n")
        yamlFile.close()

    def _open_file_dialog(self):
        # clear existing file tables                                                       ## TODO
        directory = str(QtWidgets.QFileDialog.getExistingDirectory())
        self.importPath.setText('{}'.format(directory))
        lMount = self.localMount.text()
        rMount = self.remoteMount.text()
        inplaceUserField = self.inplaceUser.text()
        inplacePassField = self.inplacePW.text()
        serverField = self.OServer.text()
        remDirectory = directory.replace(lMount, rMount, 1)
        print(remDirectory)
        fDepth = self.folderDepth.currentText()
        if fDepth == ">3":
            fDepth = "7"
        scanString = 'omero import -f --depth ' +fDepth+ ' \''+ remDirectory+'\''
        proc=subprocess.Popen(scanString, shell=True, stdout=subprocess.PIPE, universal_newlines=True)
        output=proc.communicate()[0]
        #print(output) 										For debugging only
        global fileList
        fileList = []
        try:
            client = paramiko.SSHClient()
            client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.set_missing_host_key_policy(paramiko.WarningPolicy)
            client.connect(hostname=serverField, username=inplaceUserField, password=inplacePassField)
            stdin, stdout, stderr = client.exec_command(scanString)
            stdout.channel.recv_exit_status()
            lines = stdout.readlines()
            for line in lines:
                singleLines = line.splitlines()
                for l in singleLines:
                    if not l.startswith('#'):
                        print(l)
                        fileList.append(l)
        finally:
            client.close()
            print("filelist read")
        self.createFileTable(fileList)

    def startOmeroImport(self):
        inplaceUserField = self.inplaceUser.text()
        inplacePassField = self.inplacePW.text()
        serverField = self.OServer.text()
        targetUserField = str(self.TargetUser.currentText())
        if len(targetUserField) != 0:
            bulkPath = tempdir + os.sep + "ipimp"+sessionID+".tsv"
            if os.path.isfile(bulkPath) == 1:
                importString = "omero import --sudo "+ inplaceUserField + " -w " + inplacePassField+ " -s \"" + serverField + "\" -u " + targetUserField + " --bulk /OMERO/ManagedRepository/bulki.yml"
                # print(importString) 										For debugging only
                # open the ssh and transfer the bulk and yaml files
                source1 = tempdir + os.sep +"ipimp"+sessionID+".tsv"
                dest1 = "/OMERO/ManagedRepository/ipimp"+sessionID+".tsv"
                source2 = tempdir + os.sep +"temp"+sessionID+".yml"
                dest2 = "/OMERO/ManagedRepository/bulki"+sessionID+".yml"
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
                    stdin, stdout, stderr = client.exec_command("omero import --sudo "+ inplaceUserField + " -w " + inplacePassField + " -s "+ serverField + " -u " + targetUserField + " --bulk /OMERO/ManagedRepository/bulki"+sessionID+".yml")
                    stdout.channel.recv_exit_status()
                    lines = stdout.readlines()
                    for line in lines:#										For debugging only
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
                    ## remove the old local yml and tsv files
                    os.remove(tempdir + os.sep +"ipimp"+sessionID+".tsv")
                    os.remove(tempdir + os.sep +"temp"+sessionID+".yml")
                    print("files clear")
            else:
                self.fileListMissing()
        else:
            print("no user found")
            self.showDialog()

    def setupUi(self, omeroipi):
        omeroipi.setObjectName("OMERO IPI Tool")
        omeroipi.resize(900, 600)
        
        #### line 1
        self.toolButtonOpenDialog = QtWidgets.QToolButton(omeroipi)
        self.toolButtonOpenDialog.setGeometry(QtCore.QRect(310, 10, 35, 19))
        self.toolButtonOpenDialog.setObjectName("toolButtonOpenDialog")
        self.toolButtonOpenDialog.clicked.connect(self._open_file_dialog)

        self.importPath = QtWidgets.QLineEdit(omeroipi)
        self.importPath.setEnabled(False)
        self.importPath.setGeometry(QtCore.QRect(110, 10, 191, 20))
        self.importPath.setObjectName("importPath")
        
        self.label1 = QtWidgets.QLabel(omeroipi)
        self.label1.setText('Folder to scan')
        self.label1.setGeometry(QtCore.QRect(10,10,90,20))
        self.label1.setObjectName("Label1")
        
        self.label11 = QtWidgets.QLabel(omeroipi)
        self.label11.setText('Scan Depth')
        self.label11.setGeometry(QtCore.QRect(370,10,90,20))
        self.label11.setObjectName("Label11")
        
        self.folderDepth = QComboBox(omeroipi)
        self.folderDepth.addItems(['1','2','3','>3'])
        self.folderDepth.setGeometry(QtCore.QRect(450,8,50,25))
        self.folderDepth.setObjectName("FolderDepth")
        
        logo = QPixmap("Omero_logo.png")
        self.labelImage = QtWidgets.QLabel(omeroipi)
        self.labelImage.setPixmap(logo)
        self.labelImage.setGeometry(QtCore.QRect(560,20,200,50))
        self.label1.setObjectName("Logo")
        
        #### line 2
        self.label2 = QtWidgets.QLabel(omeroipi)
        self.label2.setText('Local mount')
        self.label2.setGeometry(QtCore.QRect(10,50,90,20))
        self.label2.setObjectName("Label2")
        
        self.localMount = QtWidgets.QLineEdit(omeroipi)
        self.localMount.setEnabled(True)
        self.localMount.setGeometry(QtCore.QRect(100, 50, 90, 20))
        self.localMount.setObjectName("localMount")
        
        self.label3 = QtWidgets.QLabel(omeroipi)
        self.label3.setText('Remote mount')
        self.label3.setGeometry(QtCore.QRect(230,50,90,20))
        self.label3.setObjectName("Label3")
        
        self.remoteMount = QtWidgets.QLineEdit(omeroipi)
        self.remoteMount.setEnabled(True)
        self.remoteMount.setGeometry(QtCore.QRect(330, 50, 80, 20))
        self.remoteMount.setObjectName("remoteMount")
        
        self.generateList = QPushButton(omeroipi)
        self.generateList.setStyleSheet('QPushButton {color: black;}')
        self.generateList.setText("Generate List")
        self.generateList.setGeometry(QtCore.QRect(420,50,90,20))
        self.generateList.clicked.connect(self.buildIPIfileList)
        
        #self.Toggle = QPushButton(omeroipi)
        #self.Toggle.setStyleSheet('QPushButton {color: black;}')
        #self.Toggle.setText("Toggle")
        #self.Toggle.setGeometry(QtCore.QRect(10,70,90,20))
        #self.Toggle.clicked.connect(self.toggleChekbox)
        
        #### line 3
        self.table_place_holder = QtWidgets.QWidget(omeroipi)
        self.table_place_holder_layout = QVBoxLayout(self.table_place_holder)
        self.table_place_holder.setGeometry(QtCore.QRect(10,100,880,400))
        
        #### line 4
        self.label4 = QtWidgets.QLabel(omeroipi)
        self.label4.setText('Inplace User')
        self.label4.setGeometry(QtCore.QRect(10,520,90,20))
        self.label4.setObjectName("Label4")
        
        self.inplaceUser = QtWidgets.QLineEdit(omeroipi)
        self.inplaceUser.setEnabled(True)
        self.inplaceUser.setGeometry(QtCore.QRect(100, 520, 90, 20))
        self.inplaceUser.setObjectName("inplaceUser")
        
        self.label5 = QtWidgets.QLabel(omeroipi)
        self.label5.setText('Password')
        self.label5.setGeometry(QtCore.QRect(230,520,90,20))
        self.label5.setObjectName("Label5")

        self.inplacePW = QtWidgets.QLineEdit(omeroipi)
        self.inplacePW.setEnabled(True)
        self.inplacePW.setEchoMode(self.inplacePW.Password)
        self.inplacePW.setGeometry(QtCore.QRect(300, 520, 90, 20))
        self.inplacePW.setObjectName("inplacePW")
        
        self.label6 = QtWidgets.QLabel(omeroipi)
        self.label6.setText('Server')
        self.label6.setGeometry(QtCore.QRect(410,520,90,20))
        self.label6.setObjectName("Label6")

        self.OServer = QtWidgets.QLineEdit(omeroipi)
        self.OServer.setEnabled(True)
        self.OServer.setGeometry(QtCore.QRect(460, 520, 110, 20))
        self.OServer.setObjectName("OServer")
        
        self.label7 = QtWidgets.QLabel(omeroipi)
        self.label7.setText('Target User')
        self.label7.setGeometry(QtCore.QRect(590,520,90,20))
        self.label7.setObjectName("Label7")
        
        self.TargetUser = QComboBox(omeroipi)
        self.TargetUser.setEnabled(True)
        self.TargetUser.setGeometry(QtCore.QRect(680, 520, 110, 20))
        self.TargetUser.setObjectName("TargetUser")
        self.TargetUser.addItems(userList)
        
        #### line 5
        self.label8 =  QtWidgets.QLabel(omeroipi)
        self.label8.setText('Start Import')
        self.label8.setGeometry(QtCore.QRect(10,550,90,20))
        self.label8.setObjectName("Label8")
        
        self.startImport = QPushButton(omeroipi)
        self.startImport.setStyleSheet('QPushButton {color: black;}')
        self.startImport.setText("Start")
        self.startImport.setGeometry(QtCore.QRect(100,550,90,20))
        self.startImport.clicked.connect(self.startOmeroImport)
        
        self.closeAll = QPushButton(omeroipi)
        self.closeAll.setStyleSheet('QPushButton {color: black;}')
        self.closeAll.setText("Quit")
        self.closeAll.setGeometry(QtCore.QRect(240,550,90,20))
        self.closeAll.clicked.connect(app.instance().quit)
        
        self.label10 =  QtWidgets.QLabel(omeroipi)
        self.label10.setText('Server Settings')
        self.label10.setGeometry(QtCore.QRect(590,550,110,20))
        self.label10.setObjectName("Label9")
        
        self.openSettings = QPushButton(omeroipi)
        self.openSettings.setStyleSheet('QPushButton {color: black;}')
        self.openSettings.setText("Settings")
        self.openSettings.setGeometry(QtCore.QRect(700,550,90,20))
        self.openSettings.clicked.connect(self.settingsWindow)
        
        # read settings from stored settings if exist
        if os.path.isfile("ipisettings.p") == 1:
            read_settings = pickle.load( open( "ipisettings.p", "rb" ) )
            # print(read_settings) 										For debugging only
            self.localMount.setText(read_settings["localMount"])
            self.remoteMount.setText(read_settings["remoteMount"])
            self.inplaceUser.setText(read_settings["inplaceUser"])
            self.inplacePW.setText(read_settings["inplacePass"])
            self.OServer.setText(read_settings["OmeroServer"])
            # generate the user list from the omero server
            inplaceUserField = self.inplaceUser.text()
            inplacePassField = self.inplacePW.text()
            serverField = self.OServer.text()
            try:
                client = paramiko.SSHClient()
                client.load_system_host_keys()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                client.set_missing_host_key_policy(paramiko.WarningPolicy)
                client.connect(hostname=serverField, username=inplaceUserField, password=inplacePassField)
                listUserString = "omero user list --style plain -u " + inplaceUserField + " -w " + inplacePassField + " -s "+ serverField
                stdin, stdout, stderr = client.exec_command(listUserString)
                stdout.channel.recv_exit_status()
                lines = stdout.readlines()
                for line in lines:
                    cells = line.split(',')
                    if len(cells)>2:
                        userList.append(cells[1])
                userList.remove('root')
                userList.remove('guest')
                userList.remove('inplace')
                self.TargetUser.addItems(userList)
            finally:
                client.close()
                print("user list imported")
        else:
            self.settingsWarning()
            
        self.retranslateUi(omeroipi)
        QtCore.QMetaObject.connectSlotsByName(omeroipi)

    def retranslateUi(self, omeroipi):
        _translate = QtCore.QCoreApplication.translate
        omeroipi.setWindowTitle(_translate("omeroipi", "OMERO IPI Tool"))
        self.toolButtonOpenDialog.setText(_translate("omeroipi", "..."))

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
         

    
if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(QIcon('IPI_icon.png'))
    omeroipi = QtWidgets.QDialog()
    ui = Ui_omeroipi()
    ui.setupUi(omeroipi)
    omeroipi.show()

    sys.exit(app.exec_())