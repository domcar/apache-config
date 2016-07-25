#!/usr/bin/python

import sys, json, os, re, glob, platform
import StringIO
import collections

# receives a line with Include statement and returns a list of files in alphabetical order
def find_files(line,apachedir):
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

# prints the lines of the file, only empty lines and comments are excluded
def print_raw_config(f,apache_dir,raw):
    input_file = open(f,'r')
    for line in input_file:
        if not line.lstrip() : continue                    # avoid empty lines
        result = what_is(line)
        if result == 'comment': continue                   # avoid comments
        if result == 'Include':                            # if other files are included we need to know which ones
           list_files = find_files(line,apache_dir)
           for each in list_files:                         # then print the files
               print_raw_config(each,apache_dir,raw)
           continue                                        # do not print the Include line
        print >> raw, line.strip("\n")                     # only after each Included file has been printed continue with the original file

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

    if re.match('<[a-z-A-Z]',line):
       return 'section'
    if re.match('</',line):
       return 'end'


# Parsing the <IfModule> section
# if the module is active than go to parse section
# if not active we can simply jump the all section, that is, not printing anything
def check_IFmodule(all_modules,line, old, new, all_defines):
    try:
       module_name = line.lstrip().split()[1].rsplit(".")[0].replace('>',"")
    except:
       module_name = line.lstrip().split()[1].replace('>',"")

    if module_name in all_modules:          # if the module is loaded we continue as usual
        check_sections(all_modules,all_defines, old,new)
    else:                                   # if not loaded we ignore the all section (we go recursive to avoid a nested </IfModule>)
        for line in old:
            result = what_is(line)
            if result == 'IfModule':        # if there is a nested IfModule we have to go recursive
               check_IFmodule(all_modules,line, old, new, all_defines)
            elif result == 'endIfModule':
               return
            else:
               continue

def check_IfDefine(all_modules, line, old, new, all_defines):
    define = line.lstrip().split()[1].replace('>',"")

    if define in all_defines:               # if the Defines is loaded continue as usual
       check_sections(all_modules, all_defines, old, new)
    else:
        for line in old:                    # if not loaded we ignore the all section (we go recursive to avoid a nested </IfDefine>)
            result = what_is(line)
            if result == 'IfDefine':        # if there is a nested IfDefine we have to go recursive
               check_IfDefine(all_modules, line, old, new, all_defines)
            elif result == 'endIfDefine':
               return
            else:
               continue

def add_module(all_modules, line):
    module1 = line.split()[1]
    module2 = line.split()[2].rsplit("/",1)[1].rsplit(".")[0]
    all_modules.append(module1)
    all_modules.append(module2)

def add_define(all_defines, line):
    define = line.split()[1]
    all_defines.append(define)



# let's analyse the data that we have so far: we have one single file with all the configuraton of Apache
# if a line is a key : values, we don't need to do anything, this is a global valid key
# if a line starts with <If Module> we need to check if that Module is active or not
# if not, ignore the all section until we find </IfModule>
# the other sections are at the momet left as they are 
def check_sections(all_modules, all_defines, old, new):
    for line in old:
        result = what_is(line)

        if result == 'LoadModule':
           add_module(all_modules,line)
           continue

        if result == 'Define':
           add_define(all_defines,line)
           continue

        if result == 'key':
           print >> new, line.strip("\n")
        if result == 'comment':
           continue

        if result == 'section':
           print >> new, line.strip("\n")
           check_sections(all_modules, all_defines, old, new)
        if result == 'end':
           print >> new, line.strip("\n")
           return
   
        if result == 'IfModule':
           check_IFmodule(all_modules,line, old, new, all_defines)
        if result == 'endIfModule':
           return

        if result == 'IfDefine':
           check_IfDefine(all_modules,line, old, new, all_defines)
        if result == 'endIfDefine':
           return

def make_xml(old, new):
    print >> new, '<Start>'
    for line in old:
        result = what_is(line)
 
        if result == 'key':
           tag = line.lstrip().split()[0]
           value = line.split(tag)[1].lstrip().strip("\n")
           indent = line.split(tag)[0]
           print >> new, indent+'<'+tag+'>'+value+'</'+tag+'>'
        elif result == 'section':
           tag = line.lstrip().split()[0].replace('<',"")
           attribute = line.split(tag)[1].lstrip().strip("\n").replace('>',"")
           indent = line.split('<'+tag)[0]
           if re.match("\"",attribute):
              print >> new, indent+'<'+tag+' attr='+attribute+'>'
           else:
              print >> new, indent+'<'+tag+' attr='+'"'+attribute+'"'+'>'
        elif result == 'end':
           print >> new, line.strip("\n")
    print >> new, '</Start>'

def make_json(old, attribute):
    try:
       config = collections.OrderedDict()
    except:
       config = {} #for python <2.7
    config['@Location'] = attribute
    for line in old:
        result = what_is(line)
 
        if result == 'key':
            key = line.lstrip().split()[0]
            value = line.split(key)[1].lstrip().strip("\n")
            if key not in config:
                   config[key] = value
            else:
                   if isinstance(config[key],list):
                      config[key].append(value)
                   else:
                      temp = config[key]
                      config[key] = []
                      config[key].append(temp)
                      config[key].append(value)

        elif result == 'section':
             key = line.lstrip().split()[0].replace('<',"")
             attribute = line.split(key)[1].lstrip().strip("\n").replace('>',"")
             if key not in config:
                   config[key] = []
                   new = make_json(old, attribute)
                   config[key].append(new)
             else:
                   new = make_json(old, attribute)
                   config[key].append(new)
        elif result == 'end':
           return config

    return config
              
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

    raw = StringIO.StringIO()  # we work with buffer instead of files
    #raw =  open('raw','a')    # in case you want to see the file raw uncomment
    print_raw_config(input_file,apache_dir,raw) 
    #raw.close()              

    old = StringIO.StringIO(raw.getvalue())
    #old = open('raw')
    new = open('after_check_sections','aw')
    all_modules = []
    all_defines = []
    check_sections(all_modules, all_defines, old, new)
    old.close()
    new.close()

    old = open('after_check_sections')
    #new = open ('finale.xml','aw')
    #make_xml(old, new)
    #new.close()
    attribute = 'general'
    config = make_json(old, attribute)

    #with open('finale.xml') as f:
    #    d = xmltodict.parse(f)
    with open('risultato.json','w') as outfile:
         json.dump(config,outfile,indent=3, sort_keys=False)
