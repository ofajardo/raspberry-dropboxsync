#!/usr/bin/env python
"""
Simple script to synchronize a directory in raspberry pi with a Dropbox Application

Setup: 
* Create a Dropbox Application and get the token. 
* The first time, upload all the files you want to synchronize to the Dropbox application folder.
  This is important because the first time the script will just download everything from dropbox to local, 
  overwriting whatever you have in there!
* Save the token to a text file ".dropbox_token"
* Put the token file in the root of the raspberry pi folder you
  want to synchronize.
* Copy this script to that folder and execute it from there, or edit the variable SYNC_DIR in this 
  script.

What does it do?

The first time it gets executed, it will download everything on your
dropbox application and create a .dropbox_state file saving the sate. 
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

"""
__author__ = "ofajardo"

import os
import pickle
import dropbox

class DropboxSync:
    """
    Class to synchronize a local folder with a drobpox application.
    """
    
    def __init__(self, token_file_path, state_file_path):
        
        self.token_file_path = token_file_path
        self.state_file_path = state_file_path
        
        self.local_files = {}
        self.remote_files = {}
        self.local_dirs = {}
        self.remote_dirs = {}
        
        #create the client
        token = self.get_token()
        self._get_client(token)
        
    def get_token(self):
        """
        reads the Dropbox application token from a text file.
        """
        f = open(self.token_file_path)
        token = f.read().strip()
        return token
        
    def _get_client(self, token):
        """
        get the client with api v2. 
        """
        self.dropbox_client = dropbox.Dropbox(token)
        
    def load_state(self):
        """
        Loads the status from file
        """
        
        fyle = open(STATE_FILE,'rb')
        data = pickle.load(fyle)
        fyle.close()
        self.local_files = data['local_files']
        self.remote_files = data['remote_files']
        self.local_dirs = data['local_dirs']
        self.remote_dirs = data['remote_dirs']
     
    def save_state(self):
        """
        Dumps the critical variables holding the status to a file
        """
        
        data = {'local_files':self.local_files, 'remote_files':self.remote_files,
                'local_dirs':self.local_dirs, 'remote_dirs':self.remote_dirs}
        fyle = open(self.state_file_path,'wb')
        pickle.dump(data,fyle, -1)
        fyle.close()
        
    def download_all(self, path = ''):
        """
        Downloads everything from server to local
        """
        
        filelist = self._listfiles(path=path)
        for dfile in filelist.entries:
            path = dfile.path_display[1:]
            if isinstance(dfile, dropbox.files.FileMetadata):
                self.download(path) # trim root slash
            elif isinstance(dfile, dropbox.files.FolderMetadata):
                self.create_local_folder(path)
                self.local_dirs[path] = {'modified': os.path.getmtime(path)}
                self.remote_dirs[path] = dfile
    
    
    def sync_server(self, path = '', ignore_path = None):
        """
        Compares old server status with current server status
        """
        
        # use ignore_path to prevent download of recently uploaded files
        
        # iterate over files in server
        delta = self._listfiles(path=path)
        current_files = list()
        current_folders = list()
        for entry in delta.entries:
            
            path = entry.path_display[1:]
            if path != ignore_path and path!=STATE_FILE:            
            
                if isinstance(entry, dropbox.files.FileMetadata):
                    current_files.append(path)
                    # file in server but not in remote
                    if path not in self.remote_files:
                        print('\n\tNot in local')
                        self.download(path)
                    # server revision is newer than in remote
                    elif entry.rev != self.remote_files[path].rev:
                        print('\n\tOutdated revision')
                        self.download(path)
                elif isinstance(entry, dropbox.files.FolderMetadata):
                    current_folders.append(path)
                    if path not in self.remote_dirs:
                        self.create_local_folder(path)
                        self.remote_dirs[path] = entry
                        self.local_dirs[path] = {'modified': os.path.getmtime(path)}

        # iterate over remote to delete local files deleted on the server
        for curpath, entry in list(self.remote_files.items()):
            if curpath not in current_files:
                print('\n\tRemoving File:%s' % curpath)
                os.remove(curpath)
                del self.local_files[curpath]
                del self.remote_files[curpath]
        # iterate over remote to delete folders deleted on the server
        for curpath, entry in list(self.remote_dirs.items()):
            if curpath not in current_folders:
                print('\n\tRemoving Folder:%s' % curpath)
                os.rmdir(curpath)
                del self.local_dirs[curpath]
                del self.remote_dirs[curpath]
                
    def sync_local(self):
        """
        Compares old local files with current local files 
        """
        # Checking for new local folders
        folderlist = []
        for root, dirnames, filenames in os.walk('.'):
            for dirname in dirnames:
                curdir = os.path.join(root, dirname)
                if curdir != root:
                    folderlist.append(curdir[2:])
                    
        for new_folder in folderlist:
            self.check_local_folder(new_folder)
        
        # Checking for new or updated local files
        filelist = []
        for root, dirnames, filenames in os.walk('.'):
            for filename in filenames:
                if filename != STATE_FILE:
                    filelist.append(os.path.join(root, filename)[2:])
        
        for new_file in filelist:
            self.check_local_file(new_file)
            
        # Checking for deleted local files
        old_list = list(self.local_files.keys())
        filelist_unixstyle = [x.replace('\\', '/') for x in filelist]
        for old_file in old_list:
            if old_file not in filelist_unixstyle:
                self.delete_remote_file(old_file)
                    
        # Checking for deleted local folders
        old_list = list(dropbox_sync.local_dirs.keys())
        folderlist_unixstyle = [x.replace('\\', '/') for x in folderlist]
        for old_folder in old_list:
            if old_folder not in folderlist_unixstyle:
                self.delete_remote_folder(old_folder)
 
    def download(self, path):
        """
        Downloads a file from the server
        """
        print('\tDownloading: %s' % path)
        head, tail = os.path.split(path)
        # make the folder if it doesn't exist yet
        if head and not os.path.exists(head):
            raise Exception('folder %s does not exist!' % head)            
        # download to file
        meta = self.dropbox_client.files_download_to_file(path, os.path.join('/',path))
        # add to local repository
        self.local_files[path] = {'modified': os.path.getmtime(path)}
        self.remote_files[path] = meta
    
    def upload(self, path):
        """
        Uploads a file to the server
        """
        print('\tUploading: %s' % path)
        local = open(path,'rb')
        checkpath = path.replace('\\', '/')
        meta = self.dropbox_client.files_upload(local.read(), os.path.join('/',checkpath), mode=dropbox.files.WriteMode('overwrite', None))
        local.close()
        
        self.local_files[checkpath] = {'modified': os.path.getmtime(path)}
        self.remote_files[checkpath] = meta
        
        # clean out the delta for the file upload
        #self.execute_delta(dropbox_client, ignore_path=meta.display_path)
        
    def create_remote_folder(self, path):
        """
        Creates a remote folder
        """
        print('\tCreating folder in server: %s' % path)
        checkpath = path.replace('\\', '/')
        meta = self.dropbox_client.files_create_folder(os.path.join('/',path), autorename=False)
        
        self.local_dirs[checkpath] = {'modified': os.path.getmtime(path)}
        self.remote_dirs[checkpath] = meta
        
    def create_local_folder(self,path):
        """
        Creates a local dir if it does not exists yet.
        """
        if not os.path.exists(path):
            print('creating folder: %s' % path)
            os.makedirs(path)
        else:
            if not os.path.isdir(path):
                raise Exception('path %s is not a directory' % path)
    
    def delete_remote_file(self, path):
        """
        Deletes a file in the server
        """
        print('\tFile deleted locally. Deleting on Dropbox: %s' % path)
        path = path.replace('\\','/')
        try:
            self.dropbox_client.files_delete(os.path.join('/',path))
        except:
            # file was probably already deleted
            print('\tFile already removed from Dropbox')
            
        del self.local_files[path]
        del self.remote_files[path]
        
    def delete_remote_folder(self, path):
        """
        Deletes a folder in the server
        """
        print('\tFolder deleted locally. Deleting on Dropbox: %s' % path)
        path = path.replace('\\','/')
        try:
            self.dropbox_client.files_delete(os.path.join('/',path))
        except:
            # file was probably already deleted
            print('\tFile already removed from Dropbox')
            
        del self.local_dirs[path]
        del self.remote_dirs[path]
        
    
    def check_local_file(self, path):
        """
        Checks current local file against old local files
        """
        # lets see if we've seen it before
        checkpath = path.replace('\\', '/')
        if checkpath not in self.local_files:
            # upload it!
            self.upload(path)
        elif os.path.getmtime(path) > self.local_files[checkpath]['modified']:
            # newer file than last sync
            self.upload(path)
            
    def check_local_folder(self, path):
        """
        Checks current local folder against old local folder
        """
        checkpath = path.replace('\\', '/')
        if checkpath not in self.local_dirs:
            self.create_remote_folder(path)
            
    def _listfiles(self, path = ''):
        """
        Gives back a list of all files in the application.
        """
        filelist = self.dropbox_client.files_list_folder(path, recursive=True)
        return filelist


    
if __name__ == '__main__':
   
    print( """
****************************************
*     Dropbox File Syncronization      *
****************************************""")
 
    STATE_FILE = '.dropbox_state'
    TOKEN_FILE = ".dropbox_token"
    SYNC_DIR = ""
    
    if SYNC_DIR:
        os.chdir(SYNC_DIR)

    if not os.path.isfile(TOKEN_FILE):
        raise Exception("Please create a file %s with the application token in it" % TOKEN_FILE)    
    
    dropbox_sync = DropboxSync(TOKEN_FILE, STATE_FILE)

    if os.path.isfile(STATE_FILE):
        print('\nLoading State')
        dropbox_sync.load_state()
        print('\nSync folders and files from server')
        dropbox_sync.sync_server()
        print('\nSync folders and files from local')
        dropbox_sync.sync_local()        
    else:
        print('\nCannot find state file ...')
        print('\nDownloading everything from Dropbox')
        dropbox_sync.download_all()
        
    print('\nSaving state')
    dropbox_sync.save_state()

    print('\nSync complete')
