# raspberry-dropboxsync
Simple script to synchronize a directory in raspberry pi with a Dropbox Application

Setup: 
* Create a Dropbox Application and get the token. 
* Save the token to a text file ".dropbox_token"
* Put the token file in the root of the raspberry pi folder you
  want to synchronize.
* Copy this script to that folder and execute it from there, or edit the variable SYNC_DIR in this 
  script.

What does it do?

The first time it gets executed, it will download everything on your
dropbox application and create a .dropbox_state file saving the sate. Then it
will upload any new folders to dropbox.
This means it will overwrite local files, get a copy of your latest local files
to dropbox before executing this script the first time!.

The next time, it will first compare the files currently in the server with the
files in the server saved in the state file. It will synchronize the local files
to those currently in the server. Next, it will check if there are changes
in the local folders and files and synchronize with the server. This means
the server has precedence over the local files. 

The synchronization is bi-directional (not the first time the script gets
executed!). The script should work both on Linux and Windows. Requires that
dropbox python API is installed (you can install it by "pip install dropbox",
be sure you are using version 8 at least and that previous versions have been
completely removed).

This script is based on an old one I found on github, which was using the
APIv1. Unfortunately I could neither find the original script (so I cannot
reference it here) nor did I find a script using the Api V2. Therefore I 
decided to adapt the old script to work with the dropbox APi V2.

It's a bit experimental. Use at your own risk!
