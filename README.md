# Readme

## Background
This is a python based GUI for OMERO Inplace import workflows. The tools provides a simple GUI for the regular user to enter files to the OMERO server without the need to copy the binary pixel data to the server. The original binary pixel data is kepped on a central file server, that is accessed from both the OMERO server and the client used to start the import. This is done following the inplace import szenary described here: https://docs.openmicroscopy.org/omero/5.6.1/sysadmins/in-place-import.html. The tool then generates a bulk import yaml file together with a second file containing the file list of images to be imported. This is done according to: https://docs.openmicroscopy.org/omero/5.6.1/users/cli/import-bulk.html.

## Prerequest
The server must have a permanent mount point of the file server. User righs must be set so that the omero system user as well as the inplace user have access to the image files to be loaded. Additionally an inplace user must be set up on the OMERO server that has full read/write access to the OMERO/ManagedRepository. This is described in detail here: https://docs.openmicroscopy.org/omero/5.6.1/sysadmins/in-place-import.html. 

## Installation
