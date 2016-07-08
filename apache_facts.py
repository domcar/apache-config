#!/bin/usr/python

import sys, json, os, re, glob, platform

DOCUMENTATION = '''
---
module: gather_apache_facts; tested on Ubuntu 10,12,14,16 and Centos 6,7 with apache 2.2, 2.4
author:
    - "Domenico Caruso" domenico.caruso@de.clara.net
short_description: Provide facts regarding apache

prerequisites: 

description: it reads the apache2.conf and prints which files will be read by apache (mods-enabled, sites-enabled. ports.conf, conf-enabled)
             it also reads each of these files (and apache2.conf) and print the configuration (see example)

options:
    type:
        required: True 
        description: ["The wanted config file data type"]
        choices: ['configuration','enabled']
'''

EXAMPLES = '''
this part comes from reading the apache2.conf
    "clara_apache_enabled": {
        "apache2": {
            "ports.conf": "enabled"
        },
        "conf-enabled": {
            "charset.conf": "enabled",
            "localized-error-pages.conf": "enabled",
            "other-vhosts-access-log.conf": "enabled",
            "security.conf": "enabled",
            "serve-cgi-bin.conf": "enabled"
        },
        "mods-enabled": {
            "access_compat.load": "enabled",
            "alias.conf": "enabled",
            "alias.load": "enabled",
            "auth_basic.load": "enabled",
            "authn_core.load": "enabled",
            "authn_file.load": "enabled",
        .
        .
        .
        .
        .
this part comes from reading each configuration file:
        "ports.conf": {
                "<IfModule mod_gnutls.c>\n": {
                    "Listen": "443 "
                },
                "<IfModule ssl_module>\n": {
                    "Listen": "443 "
                },
                "Listen": "80 "
            }
        },
        "conf-enabled": {
            "charset.conf": {},
            "localized-error-pages.conf": {},
            "other-vhosts-access-log.conf": {
                "CustomLog": "${APACHE_LOG_DIR}/other_vhosts_access.log vhost_combined "
            },
            "security.conf": {
                "ServerSignature": "On ",
                "ServerTokens": "OS ",
                "TraceEnable": "Off "
            },
'''

def sub_section (f,configuration):
    for line in f:
         line = line.lstrip()
         if line.isspace(): continue
         if not line : continue
         if re.match('#',line): continue # avoid comments
         if re.match('</',line):
            return
         if not re.match('<',line):
            key = line.replace('\t'," ").replace('\n'," ").split(" ",1)[0]
            value = line.replace('\t'," ").replace('\n'," ").split(" ",1)[1]
            if key in configuration:
               configuration[key] = configuration[key]+"; " + value
            else:
               configuration[key] = value
            continue
         if re.match('<',line):
            new_dict = line.strip("\n")
            if new_dict not in configuration:
               configuration[new_dict]={}
            sub_section(f, configuration[new_dict]) 

def check_module(f,all_modules,ifmodule):
    for line in  f:
        line = line.lstrip()
        if line.isspace(): continue
        if not line : continue
        if re.match('#',line): continue # avoid comments
        if re.match('</',line):
           return
        module_name = line.rsplit("/",1)[1].strip('\n')
        if ifmodule in all_modules:
           all_modules.append(module_name)


def files_folders():
    all_files=[]
    all_folders= []
    # check what OS is this and adds the first file to the list
    if platform.dist()[0] == 'Ubuntu':
       apache_dir = '/etc/apache2/'
       f = open('/etc/apache2/apache2.conf','r')
       all_files.append('/etc/apache2/apache2.conf')
    else:
       apache_dir = '/etc/httpd/'
       f = open('/etc/httpd/conf/httpd.conf','r')
       all_files.append('/etc/httpd/conf/httpd.conf')
    # it reads the config file and appends to the list the files that will be usued by apache
    for line in f:
        if re.match('Include',line):
           line = line.split()[1]
           if os.path.isfile(apache_dir+line):
              all_files.append(apache_dir+line)
           elif os.path.isfile(line):
              all_files.append(line)
           else:
              folder_name=line.rsplit("/",1)[0]
              try:
                 extension = "/*."+line.rsplit(".",1)[1]
              except:
                 extension = '/*'
              if apache_dir not in folder_name:
                 join = apache_dir+folder_name
              else:
                 join = folder_name
              if join not in all_folders:
                 all_folders.append(join)
              all_files.extend(glob.glob(join+extension))
    return all_files,all_folders

# ENABLED
enabled = {}
enabled['enabled_modules'] = {}
all_files, all_folders = files_folders()
all_modules = [] 
for file_path in all_files:
    file_name = os.path.basename(file_path)
    folder_name= os.path.dirname(file_path).rsplit("/",1)[1]                                             
    if folder_name == "mods-enabled" or folder_name == "conf.modules.d": # this IF checks which modules are enabled
       if ".load" in file_path or folder_name == "conf.modules.d":
           with open(file_path,'r') as f:                                                                    
                for line in  f:
                    line = line.lstrip()
                    if re.match('<',line):
                       ifmodule = "mod_"+line.split()[1].replace('>',"").replace("_module",".so")
                       check_module(f,all_modules,ifmodule)
                       continue
                    elif re.match('Load',line):
                       module_name = line.rsplit("/",1)[1].strip('\n')
                       all_modules.append(module_name)
                    else:
                      continue
    if file_path == '/etc/apache2/apache2.conf' or file_path == '/etc/httpd/conf/httpd.conf': # # this IF checks which modules are enabled (for centos6)
       with open(file_path,'r') as f:
                for line in  f:
                    line = line.lstrip()
                    if re.match('Load',line):
                       module_name = line.rsplit("/",1)[1].strip('\n')
                       all_modules.append(module_name)
                    else:
                      continue
    if all_modules:
       for each in all_modules:
           enabled['enabled_modules'][each] = 'enabled' 
    if folder_name not in enabled: # this tells us which file are being read (usued) by apache service
       enabled[folder_name] = {}
    enabled[folder_name][file_name] = 'enabled' 


# CONFIGURATION
configuration = {}
all_files, all_folders = files_folders()

for file_path in all_files:
    file_name = os.path.basename(file_path)
    folder_name= os.path.dirname(file_path).rsplit("/",1)[1] 
    if folder_name == 'mods-enabled' or folder_name == 'conf.modules.d': continue # ignore the conf of mods
    if folder_name not in configuration:
       configuration[folder_name] = {}
    configuration[folder_name][file_name] = {}
    f = open(file_path,'r')
    for line in f:
        line = line.lstrip()
        if not line : continue
        if re.match('#',line): continue # avoid comments
        elif re.match('Include',line): continue # avoid ohter files
        elif re.match('Load',line): continue # avoid the modules
        elif re.match('<',line):
           new_dict = line.strip("\n")
           if new_dict not in configuration[folder_name][file_name]:
              configuration[folder_name][file_name][new_dict]={}
           sub_section(f, configuration[folder_name][file_name][new_dict])
        else:
           key = line.replace('\t'," ").replace('\n'," ").split(" ",1)[0]
           value = line.replace('\t'," ").replace('\n'," ").split(" ",1)[1]
           if key in configuration[folder_name][file_name]:
               configuration[folder_name][file_name][key] = configuration[folder_name][file_name][key]+"; " + value
           else:
               configuration[folder_name][file_name][key] = value 

with open('risultato.txt','w') as outfile:
     json.dump(enabled,outfile,indent=1)
with open('risultato.txt','aw') as outfile:
     json.dump(configuration,outfile,indent=1)
