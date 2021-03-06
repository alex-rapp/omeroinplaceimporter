## 2020-07-03: v02

* added session number to allow simultaneous import from several sources
* check that User field is not empty to avoid orphan images

## 2020-07-05: v03
* changed folder scanning to run on the Omero server as suggested by Damir:
  https://forum.image.sc/t/inplace-importer-in-omero-script/27131/9
* check that the bulk import files were generated

## 2020-07-07: v04
* removed the bug, that the table is not updated when a new folder is selected, see:
  https://stackoverflow.com/questions/62770315/pyqt5-update-replace-a-qtablewidget-inside-a-qscrollarea?answertab=votes#tab-top

## 2020-07-08: v05
* added a drop down user list, that is populated from the omero server by running "omero user list", this is to prevent empty entries or miss typed users

## 2020-07-09: v06
* added the option to set the imported images to read only on the file server. This feature requries that the users is the owner of the files and has read/write permission.

## 2021-03-01: v07
* fixed an error where user names with spaces causes errors
