#!/usr/bin/python

import sys, json, os, re, glob, platform
import StringIO
import collections
import xml.etree.ElementTree as ET

# receives a line with Include statement and returns a list of files in alphabetical order
def find_files(line):
    all_files = []
    line = line.split()[1]
    if os.path.isfile(apache_dir+line):      # check if the include was a file name, e.g., ports.conf, or directory/filename
       all_files.append(apache_dir+line)
    elif os.path.isfile(line):               # check if it was a full path, e.g., /etc/apache2/ports.conf
       all_files.append(line)
    else:                                    # or if it was a directory, e.g., mods-enabled/*.conf
       folder_name = line.rsplit("/",1)[0]
       try:
          extension = "/*."+line.rsplit(".",1)[1]
       except:
          extension = '/*'
       if apache_dir not in folder_name:
          join = apache_dir + folder_name
       else:
          join = folder_name
       all_files.extend(glob.glob(join+extension))
    all_files.sort()                         # alphabetically ordered because this is how Apache reads the files
    return all_files


# parsing function to know what line are we dealing with
def what_is(line):
    line = line.lstrip()

    if re.match('#',line):
       return 'comment'

    if re.match('Include',line):
       return 'Include'

    if re.match('LoadModule', line):
       return 'LoadModule'

    if re.match('Define', line):
       return 'Define'

    if re.match('[a-zA-Z]',line):
       return 'key'

    if re.match('<IfModule', line):
       return 'IfModule'
    if re.match('</IfModule', line):
       return 'endIfModule'

    if re.match('<IfDefine', line):
       return 'IfDefine'
    if re.match('</IfDefine', line):
       return 'endIfDefine'

    if re.match('<Directory ', line): # notice the space
       return 'Directory'
    if re.match('</Directory>', line):
       return 'endDirectory'

    if re.match('<[a-z-A-Z]',line):
       return 'section'
    if re.match('</',line):
       return 'end'


# Parsing the <IfModule> section
# if the module is active than go to parse section
# if not active we can simply jump the all section, that is, not printing anything
def check_IFmodule(line, old, new):
    try:
       module_name = line.lstrip().split()[1].rsplit(".")[0].replace('>',"")
    except:
       module_name = line.lstrip().split()[1].replace('>',"")

    if module_name in all_modules:          # if the module is loaded we continue as usual
        parse_apache(old,new)
    else:                                   # if not loaded we ignore the all section (we go recursive to avoid a nested </IfModule>)
        for line in old:
            result = what_is(line)
            if result == 'IfModule':        # if there is a nested IfModule we have to go recursive
               check_IFmodule(line, old, new)
            elif result == 'endIfModule':
               return
            else:
               continue

def check_IfDefine(line, old, new):
    define = line.lstrip().split()[1].replace('>',"")

    if define in all_defines:               # if the Defines is loaded continue as usual
       parse_apache(old, new)
    else:
        for line in old:                    # if not loaded we ignore the all section (we go recursive to avoid a nested </IfDefine>)
            result = what_is(line)
            if result == 'IfDefine':        # if there is a nested IfDefine we have to go recursive
               check_IfDefine(line, old, new)
            elif result == 'endIfDefine':
               return
            else:
               continue


# the main parsing function:
# if we get a key:value nothig to do, just print
# if LoadModule we add the Module to the list of loaded modules
# same thing for Define
# when the line is Include: call another function that returns the list of included files
# if section (no <if>) print the section 
def parse_apache(old, new):
    for line in old:
        if not line.lstrip() : continue
        result = what_is(line)

        if result == 'LoadModule':
           module1 = line.split()[1]
           module2 = line.split()[2].rsplit("/",1)[1].rsplit(".")[0]
           all_modules.append(module1)
           all_modules.append(module2)
           continue

        if result == 'Define':
           define = line.split()[1]
           all_defines.append(define)
           continue

        if result == 'key':
           print >> new, line.strip("\n")

        if result == 'comment':
           continue

        if result == 'Include':                            # if other files are included we need to know which ones
           list_files = find_files(line)
           for each in list_files:                         # then print the files
               f = open (each,'r')
               parse_apache(f,new)
               f.close()
           continue                                        # do not print the Include line


        if result == 'section':
           print >> new, line.strip("\n")
        if result == 'end':
           print >> new, line.strip("\n")

        if result == 'Directory':
           print >> new, line.strip("\n")
        if result == 'endDirectory':
           print >> new, line.strip("\n")
   
        if result == 'IfModule':
           check_IFmodule(line, old, new)
        if result == 'endIfModule':
           return

        if result == 'IfDefine':
           check_IfDefine(line, old, new)
        if result == 'endIfDefine':
           return

class Directory(object):
   'Common base class for all directory sections'

   def __init__(self, key):
      self.name = key
   
def create_dir(line,f,name):
    obj = Directory(name)
    for line in f:
        result = what_is(line)
        if result == 'endDirectory':
           return obj
        else:
           key = line.split()[0]
           value = line.split(key)[1]
           setattr(obj,key, value)

def find_dir():
    f = open ('parsed')
    global all_dirs
    all_dirs = []
    global all_obj
    all_obj = []
    for line in f:
        result = what_is(line)
        if result == 'Directory':
           try:
               name = line.lstrip().split()[1].replace('>','').strip("\"")
           except:
               name = line.lstrip().split()[1].replace('>','')
           all_dirs.append(name)
           all_obj.append(create_dir(line,f,name))
    all_dirs.sort(reverse=True)
    all_obj.sort(reverse=True)
    set_parent()
    print_parent()

def check_parenthood(child,parent):
    if parent in child:
       if parent == child:
          return
       else:
          return 'parent'

def set_parent():
    for child in all_dirs:
        for parent in all_dirs:
           if check_parenthood(child,parent) == 'parent':
              for each in all_obj: 
                  if each.name == child:
                     #print 'Setting parent ' +parent +' for child ' +each.name
                     setattr(each,'parent',parent)
              break

def print_parent():
    for each in all_obj:
        try:
           print each.name +' has as parent ' +each.parent
        except:
           print each.name +' has no parent'


if __name__ == "__main__":
    # the starting point is the main apache config file
    global apache_dir
    if platform.dist()[0] == 'Ubuntu':
       apache_dir = '/etc/apache2/'
       input_file = open (apache_dir+'apache2.conf','r')
    else:
       apache_dir = '/etc/httpd/'
       input_file = open (apache_dir+'conf/httpd.conf','r')
    global all_modules
    all_modules = []
    global all_defines
    all_defines = []
    
    # this function will start reading the main config file and print each line; when it finds an Include, it will read in aplphabetical order each file and then return to the main;
    # when it finds LoadModule or Define, it will store these into the global vars all_modules and all_defines;
    # the IfModule and IfDefine are evaluated as they are found because Apache evaluates them at startup; in case condition is not met, the all section will be jumped, else, printed
    parsed = open('parsed','aw')
    parse_apache(input_file, parsed)
    parsed.close()


    find_dir() 
