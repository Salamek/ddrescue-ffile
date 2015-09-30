#!/usr/bin/env python

import subprocess
import tempfile
import os
import hashlib
from tqdm import tqdm
import getopt
import sys

class ddr(object):
  mounted = {}
  def __init__(self, filesystem, logfile):
    self.logfile = os.path.abspath(logfile)
    self.filesystem = os.path.abspath(filesystem)
    
    if os.path.isfile(self.logfile) is False:
      raise Exception('ddrescue log file {} not found'.format(log))
      
    if os.path.isfile(self.filesystem) is False:
      raise Exception('ddrescue filesystem file {} not found'.format(filesystem))
      
  def mount(self, filesystem):
    if filesystem not in self.mounted:
      tempdir = tempfile.mkdtemp()
      try:
        self.log('Mounting filesystem {} to {}'.format(filesystem, tempdir))
        self.command(['mount', '-t', 'auto', filesystem, tempdir])
        self.log('Done.')
        self.mounted[filesystem] = tempdir
      except:
        self.log('Mounting filesystem failed')
        raise
        
    return self.mounted[filesystem]
    
  def umount(self, filesystem):
    if filesystem in self.mounted:
      try:
        self.log('Umounting filesystem {}'.format(filesystem))
        self.command(['umount', self.mounted[filesystem]])
        self.log('Done.')
        del self.mounted[filesystem]
      except:
        self.log('Umounting filesystem failed')
        raise
    
  def mounted2md5list(self, mounted):
    
    md5list = {}
    self.log('Scaning filesystem...')
    files = [os.path.join(dp, f) for dp, dn, filenames in os.walk(mounted) for f in filenames]
    self.log('Done.')

    self.log('Building MD5 checksum list...')
    
    for file in tqdm(files):
      md5list[file.replace(mounted, '')] = self.file2md5(file)

    self.log('Done.')
    return md5list
    
  def file2md5(self, path):
    hash = hashlib.md5()
    with open(path, 'rb') as f:
      for chunk in iter(lambda: f.read(4096), ""):
        hash.update(chunk)
    return hash.hexdigest()
    
    
  def command(self, command):
    if subprocess.call(command) > 0:
      raise Exception('Running command {} failed'.format(command))

  def ddrescue(self, filesystem, logfile, fill = False):
    try:
      handle, bytevalue_file = tempfile.mkstemp()
      
      f = open(bytevalue_file,'wb')
      if fill:
        self.log('Filling bad-sector blocks with non-zero bytevalue...')
        f.write('1')
      else:
        self.log('Restoring bad-sector blocks to zero bytevalue...')
        f.write(b'\x00')
      f.close()
      
      self.command(['ddrescue', '--fill=-', bytevalue_file, filesystem, logfile])
      os.remove(bytevalue_file)
      self.log('Done.')
    except:
      self.log('ddrescue command failed')
      raise

  def log(self, message):
    print(message)
    
  def start(self):
    
    ### First step - mount -> md5sum list -> umount ###
    try:
      #Mount filesystem
      mountpoint = self.mount(self.filesystem)
      
      #Calculate md5s
      md5list_original = self.mounted2md5list(mountpoint)
      
      #Umount filesystem
      self.umount(self.filesystem)
      
      ### Second step - modify bad blocks -> mount -> md5sum list -> umount -> modify bad blocks to previous state ###
      
      #Change fill bad blocks by differend data so we can detect change
      self.ddrescue(self.filesystem, self.logfile, True)
      
      #Mount filesystem again
      mountpoint = self.mount(self.filesystem)
      
      #Calculate md5s again
      md5list_modified = self.mounted2md5list(mountpoint)
      
      #Umount filesystem again
      self.umount(self.filesystem)
      
      #Revert changes to filesystem
      self.ddrescue(self.filesystem, self.logfile, False)
    
      ### Third step - check diff ###
      corupted = 0
      for patho in md5list_original:
        if md5list_modified[patho] != md5list_original[patho]:
          corupted += 1
          self.log('File {} seems corrupted, {} != {}'.format(patho, md5list_original[patho], md5list_modified[patho]))
      
      if corupted > 0:
        self.log('{} corupted files has been found :-('.format(corupted))
      else:
        self.log('All files are OK!')
      
    except:
      raise
    finally:
    # Umount all mounted 
      clear_mounts = self.mounted.copy()
      for mount in clear_mounts:
        self.umount(mount)
    
def usage():
  print('Usage:')
  print('ddfrescue [image] [logfile]')
  print('-h --help for this help')
    
if __name__ == '__main__':
  try:
      opts, args = getopt.getopt(sys.argv[1:], "h", ["help"])
  except getopt.GetoptError as err:
      # print help information and exit:
      print str(err) # will print something like "option -a not recognized"
      usage()
      sys.exit(2)
  for o, a in opts:
    if o in ("-h", "--help"):
        usage()
        sys.exit()

  
  if len(args) != 2:
    usage()
    sys.exit()

  ddr = ddr(args[0], args[1])
  ddr.start()
