#!/usr/bin/python

import sys, json, os, re, glob, platform
import StringIO

# return a list of files in alphabetical order
def find_files(line,apachedir):
    all_files=[]
    line = line.split()[1]
    if os.path.isfile(apache_dir+line):      # check if the include was a file name, e.g., ports.conf, or directory/filename
       all_files.append(apache_dir+line)
    elif os.path.isfile(line):               # check if it was a full path, e.g., /etc/apache2/ports.conf
       all_files.append(line)
    else:                                    # or if it was a directory, e.g., mods-enabled/*.conf
       folder_name=line.rsplit("/",1)[0]
       try:
          extension = "/*."+line.rsplit(".",1)[1]
       except:
          extension = '/*'
       if apache_dir not in folder_name:
          join = apache_dir+folder_name
       else:
          join = folder_name
       all_files.extend(glob.glob(join+extension))
    all_files.sort()                         # alphabetically ordered because this is how Apache reads the files
    return all_files

# prints the lines of the file, only empty lines and comments are excluded
def printare_file(f,apache_dir,raw):
    input_file = open(f,'r')
    for line in input_file:
        if not line.lstrip() : continue                    # avoid empty lines
        if re.match('#',line.lstrip()): continue           # avoid comments
        if re.match('Include',line):                       # if other files are included we need to know which ones
           list_files = find_files(line,apache_dir)
           for each in list_files:                         # then print the files
               printare_file(each,apache_dir,raw)
           continue                                        # do not print the Include line
        print >> raw, line.strip("\n")                     # only after each Included file has been printed continue with the original file



# read the raw file and when it sees LoadModule it append the module name to the list
# the reason why for each module there are 2 name is because Apache wants to make my life miserable
# there could be other LoadModule inside section <IfModule>  Load Module
# this modules will be added to the list when parsing the IfModule sections
def gets_modules():
    all_modules = []
    raw = open('raw')
    module_parsed = open ('module_parsed','w')
    for line in raw:
        if re.match('LoadModule', line):
           module1 = line.split()[1]
           module2 = line.split()[2].rsplit("/",1)[1].rsplit(".")[0]
           all_modules.append(module1)
           all_modules.append(module2)
        else:
           print >> module_parsed, line.strip("\n")
    return all_modules


# parsing function to know what line are we dealing with
# if the line startis witha letter we have a key : value and so on
# notice that each line has is left stripped
def what_is(line):
    if re.match('[a-zA-Z]',line.lstrip()):
       return 'key'
    if re.match('<IfModule', line.lstrip()):
       return 'IfModule'
    if re.match('</IfModule', line.lstrip()):
       return 'endIfModule'
    if re.match('<[a-z-A-Z]',line.lstrip()):
       return 'section'
    if re.match('</',line.lstrip()):
       return 'end'


# Parsing the <IfModule> section
# if the module is active than go to parse section
# if not active we can simply jump the all section, that is, not printing anything
def parse_IFmodule(all_modules,old,module_name):
    if module_name in all_modules:
        parse_section(old,all_modules)
    else:
        for line in old:
            result = what_is(line)
            if result == 'key':
               continue
            if result == 'section':
               continue
            if result == 'end':
               continue
            if result == 'IfModule': # if there is a nested IfModule we have to go recursive
               try:
                   module_name = line.lstrip().split()[1].rsplit(".")[0].replace('>',"")
               except:
                   module_name = line.lstrip().split()[1].replace('>',"")
               parse_IFmodule(all_modules,old,module_name)
            if result == 'endIfModule':
               return

# Here we parse the sections: the important thing here is that is line is <ifModue> we check for that modules
# all other lines are printed out 
# if the section is a <IfModule> let's check if the module is active
# if inside the section there is a LoadModule: add Module name to the all_modules list
# if is a key : value, just print the line
# if we find a nested section, we need to go call the function again

def parse_section(old,all_modules):
    for line in old:
        if re.match('LoadModule', line.lstrip()):
           module1 = line.split()[1]
           module2 = line.split()[2].rsplit("/",1)[1].rsplit(".")[0]
           all_modules.append(module1)
           all_modules.append(module2)
           continue
        result = what_is(line)
        if result == 'key':
           print line.lstrip().strip("\n")
        if result == 'section':
           print line.lstrip().strip("\n")
           parse_section(old,all_modules)
        if result == 'end':
           print line.lstrip().strip("\n")
           return
        if result == 'IfModule':
           try:
              module_name = line.lstrip().split()[1].rsplit(".")[0].replace('>',"")
           except:
              module_name = line.lstrip().split()[1].replace('>',"")
           parse_IFmodule(all_modules,old,module_name)
        if result == 'endIfModule':
           return


# let's analyse the data that we have so far: we have one single file with all the configuraton of Apache
# if a line is a key : values, we don't need to do anything, this is a global valid key
# if a line starts with <If Module> we need to check if that Module is active or not
# if not, ignore the all section until we find </IfModule>
# the other sections are at the momet left as they are 
def check_sections(all_modules):
    old = open('module_parsed')
    for line in old:
        result = what_is(line)
        if result == 'key':
           print line.lstrip().strip("\n")
        if result == 'section':
           print line.lstrip().strip("\n")
           parse_section(old,all_modules)
        if result == 'IfModule':
           try: 
              module_name = line.lstrip().split()[1].rsplit(".")[0].replace('>',"")
           except:
              module_name = line.lstrip().split()[1].replace('>',"")
           #if module_name in all_modules:
           #print module_name
           parse_IFmodule(all_modules,old,module_name)

              
if __name__ == "__main__":
    # the starting point is the main apache config file
    if platform.dist()[0] == 'Ubuntu':
       apache_dir = '/etc/apache2/'
       input_file = apache_dir+'apache2.conf'
    else:
       apache_dir = '/etc/httpd/'
       input_file = apache_dir+'conf/httpd.conf'
    
    # the following "raw" file will contain the configuration as it is read from Apache in alphabetical order
    # no parsing is applied (only comments are excluded)
    raw =  open('raw','a')
    printare_file(input_file,apache_dir,raw)
    raw.close()

    # once we have the config let's look for the lines LoadModule to see what modules are being loaded
    all_modules = gets_modules()
    os.remove('raw')            # removes file because unneeded
    
    # now that we now what modules have been loaded, let's go through the file to check the IfModule
    # here we will also make a lstrip on each line
    check_sections(all_modules)

    # now that all the IfModule have been tested we can test the IfDefine
    #check_ifdefine()
    print all_modules
