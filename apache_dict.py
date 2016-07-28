#!/usr/bin/python

import sys, json, os, re, glob, platform
import StringIO
import collections

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

    if re.match('<[dD]irectory ', line): # notice the space
       return 'Directory'
    if re.match('</[dD]irectory>', line):
       return 'endDirectory'

    if re.match('<[vV]irtualHost ', line): # notice the space
       return 'VirtualHost'
    if re.match('</[vV]irtualHost>', line):
       return 'endVirtualHost'

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

        if result == 'Location':
           print >> new, line.strip("\n")
        if result == 'endLocation':
           print >> new, line.strip("\n")

        if result == 'VirtualHost':
           print >> new, line.strip("\n")
        if result == 'endVirtualHost':
           print >> new, line.strip("\n")
   
        if result == 'IfModule':
           check_IFmodule(line, old, new)
        if result == 'endIfModule':
           return

        if result == 'IfDefine':
           check_IfDefine(line, old, new)
        if result == 'endIfDefine':
           return

################### Creating objects and setting parents  ############
# we need an object that can hold the information of each <Directory>
# so, each time we encounter a <Directory> we crate an object and set its attributes, e.g., Name, Options, Require, Allows.....
class Directory(object):
   'Common base class for all directory sections'

   def __init__(self, key):
      self.name = key


# creation of the object and attributes
# <Directory> cannot be nested: finally a good news :)
def create_object(line,f,name,TAG):
    obj = Directory(name)
    setattr(obj,'TAG', TAG)
    for line in f:
        result = what_is(line)
        if result == 'endDirectory':
           return obj
        else:
           key = line.split()[0]
           value = line.split(key)[1]
           setattr(obj,key, value)

# in case a <Directory> has been already defined, we just add the directives to the obj
def append_to_obj(f,obj):
    print obj.name
    for line in f:
        result = what_is(line)
        if result == 'endDirectory':
           return obj
        else:
           key = line.split()[0]
           value = line.split(key)[1]
           if key == 'Options':
              child_options = value.split()
              try:
                 parent_options = obj.Options.split()
                 final = merge_options(child_options, parent_options)
                 setattr(obj,key, final)
              except:
                 setattr(obj,key, value)
           else:
               setattr(obj,key, value)

# to set the right parenting order we need names to be all of same format: without quotes
def directory_name(line):
    try:
       name = line.lstrip().split()[1].replace('>','').strip("\"")                                                                                                                  
    except: 
       name = line.lstrip().split()[1].replace('>','')
    return name

# this is the main function that read the file and when finds <Directory> it call the create function
# <Directory> can be only in general config or inside a <VirtualHost>
def find_directory():
    f = open ('parsed')
    TAG = 'general'                                         # we need TAG to know where the <Directory> is located: in the general config of in a VirtualHost
    for line in f:
        result = what_is(line)
        if result == 'VirtualHost':
           TAG = line.lstrip().split()[1].replace(">","")   # setting the TAG in case VH
        if result == 'Directory':
           name = directory_name(line)
           if name in all_dirs and TAG == all_dirs[name].TAG:   # if the directory has been already defined previuosly in the file
              append_to_obj(f,all_dirs[name])
           else:                                            # otherwise we create a new object
              all_dirs[name] = create_object(line,f,name,TAG)

        if result == 'endVirtualHost':
           TAG = 'general'

    f.close()


########### setting parent to each <Directory> object ##############

def check_parenthood(child,parent):
    if child.name.startswith(parent.name):         # we compare the 2 strings, if child starts with parent: /var/www starts with /var, so /var is parent
       if parent.name == child.name: 
          return 'notparent'
       else:
          if parent.TAG == 'general' or parent.TAG == child.TAG:    # but we check also the TAG to be sure it is a parent
             return 'parent'
          else:
             return 'notparent'

# once we have all object we should set a parent for each of them
def set_parent():
    for child in sorted(all_dirs,reverse=True):
        for parent in sorted(all_dirs,reverse=True):
           if check_parenthood(all_dirs[child],all_dirs[parent]) == 'parent':
              setattr(all_dirs[child],'parent',parent)
              break



######### Merging ######################
def merge_directory_sections():
    all_dirs_VH = {}                   # we need to merge the VH <Directory> only after the general ones
    for directory in sorted(all_dirs):
        if all_dirs[directory].TAG == 'VirtualHost':  # we need to merge the VH <Directory> only after the general ones
           all_dirs_VH.append(directory) 
           continue
        check_options(all_dirs[directory])
        check_other_directives(all_dirs[directory])
    
    for directory in sorted(all_dirs_VH):     # now we can merge the VH <Directory>
        check_options(all_dirs[directory])
        check_other_directives(all_dirs[directory])


def merge_options(child_options,parent_options):
    final = []
    for option in child_options:                     # chech if options must be merged
        if '+' not in option and '-' not in option: 
            return ' '.join(child_options)           # not merging

    for option in parent_options:                    # check what options has the parent
        if not option.startswith('-') and option not in child_options and '+'+option not in child_options:
           try:
              final.append(option.replace("+",""))
           except:
              final.append(option)
    for option in child_options:                     # check what options has the child
        if not option.startswith('-') and option.strip('+') not in final:
              final.append(option.strip('+'))

    return ' '.join(final)                           # return the final options as a list

def check_options(child):
    if hasattr(child,'parent'):
       parent = all_dirs[child.parent]        # find out who is the parent
       parent_options = parent.Options.split()   # find out what Options has the parent
       try:
          child_options = child.Options.split()  # has the child Options?
       except:
          final = ' '.join(parent_options)       # if not, just inherit directly from parent
          setattr(child,'Options',final)
          child_options = child.Options.split()
          return child_options                   
       final = merge_options(child_options,parent_options)
       setattr(child,'Options',final)
       child_options = child.Options.split()
       return child_options

    else:                                        # if child has no parent, its options remain as they are
        try:
          return child.Options.split()
        except:
          setattr(child,'Options','FollowSymlinks')   # if no Options are set, the Default value is FollowSymLinks
          return child.Options.split()


def check_other_directives(child):
    if hasattr(child,'parent'):
       dict_directives_child = vars(child)
       parent = all_dirs[child.parent]
       dict_directives_parent = vars(parent)
       for directive in dict_directives_parent:
           if directive not in dict_directives_child:
              attribute = getattr(parent,directive)
              setattr(child,directive,attribute)


################# Print final configuration #####################    

def jump_directory(f):
    for line in f:
        result = what_is(line)
        if result == 'endDirectory':
           return
        else:
           continue

def write_new_directory(f1,line,indent):
    print >> f1, line.strip("\n")
    name = directory_name(line)
    for attr in vars(all_dirs[name]):
        if attr == 'parent' or attr == 'name' or attr == 'TAG':
           continue
        print >> f1, indent, attr, vars(all_dirs[name])[attr].strip("\n")
    return

def print_final():
    f = open('parsed')
    f1 = open('parsed_finale','aw')
    for line in f:
        result = what_is(line) 
        if result == 'Directory':
           indent = line.split("<")[0]
           jump_directory(f)
           write_new_directory(f1,line,indent)
           print >> f1, indent, '</Directory>'
        else:
           if re.match('Add(Icon|Language|Charset)',line.lstrip()):
              continue
           print >> f1, line.strip("\n")
    f.close()
    f1.close()



######## provides json data ##############
def make_json(old, attribute):
    try:
       config = collections.OrderedDict()
    except:
       config = {} #for python <2.7
    config['@'] = attribute
    for line in old:
        result = what_is(line)

        if result.startswith('end'):
           return config
     
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

        else:
             key = line.lstrip().split()[0].replace('<',"")
             attribute = line.split(key)[1].lstrip().strip("\n").replace('>',"")
             if key not in config:
                   config[key] = []
                   new = make_json(old, attribute)
                   config[key].append(new)
             else:
                   new = make_json(old, attribute)
                   config[key].append(new)

    return config
    

############# Main ###################
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
    
########## Parsing  ##################
    # this function will start reading the main config file and print each line; when it finds an Include, it will read in aplphabetical order each file and then return to the main;
    # when it finds LoadModule or Define, it will store these into the global vars all_modules and all_defines;
    # the IfModule and IfDefine are evaluated as they are found because Apache evaluates them at startup; in case condition is not met, the all section will be jumped, else, printed
    parsed = open('parsed','aw')
    parse_apache(input_file, parsed)
    parsed.close()


##### Creating objects for <Directory> ########
    global all_dirs
    all_dirs = {}
    find_directory()
    

#### Setting parent for each <Directory> object ###########
    set_parent()

########## Merging <Directory>  ###############
    merge_directory_sections()

######### Print final config ###############
    print_final()

######## make json ########################
    f = open('parsed_finale')
    attribute = 'server_config'
    config = make_json(f, attribute)
    with open('risultato.json','w') as outfile:
         json.dump(config,outfile,indent=3, sort_keys=False)

