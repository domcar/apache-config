# apache configuration
print in json format the apache configuration 

usage:
sudo python apache_dict.py



The final Apache config is very difficult to obtain because:
* there is not one single config file
* each file can load other files
* each key == value can be applied to everything or limited to e.g. VirtualHost, Directory etc...
* some options apply only IF something is loaded
* The merging of sections is applied is a particular order and not as it is read (http://httpd.apache.org/docs/current/sections.html#merging)

We should parse the apache config to obtain a clear view of what option is globally valid or applied only to a "subsection".

We have to procees in steps

1. __Parsing the apache configuration__:
it start reading the main config file, apache2.conf or http.conf and whenever it finds a Include statement it will read the included files. Each time it read a line like LoadModule or Define "something" it will store these values in a global list, so that it can immediately evaluate in case there is a line like: \<IfModule\> or \<IfDefine\>. The other lines are in the first moment not parsed, only printed.

2. __Find \<Directory\> (later on, every section)__:
Now that we have a file without \<IfModule\> or \<IfDefine\> we can focuse on other topics, first we will find each \<Directory\> statement. For each Directory> we will create an Object that holds the informations: Options, Require etc... Important is also to consider if \<Directory\> is located in the general config or inside a VirtualHost, because the \<Directory\> inside a VH must be merged only after the general ones, so that they can override the general config.

3. __Set Parent__: For each object we must set its parent, for example \<Directory /var/www\> will have as parent \<Directory /\> or (if present) \<Directory /var\> We must do this because the merging function must merge not in simple appearance order but in parent --> child order

4. __Merging__: Now we can finally merge the <Directory> sections. Each child will inherit from the parent its directives if that directive is not already set in child. Options directive behave differently because they inherit from parent only if all Options have a + or - before them, otherwise will remain as they are.
