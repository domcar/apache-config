# shows complete apache configuration
 

this script reads the main config file and each included file in the order as they are found. During this first reading it also stores each module and define that are Loaded so that it can immediately evaluate statements like <IfModule> or <IfDefine>. Later it proceeds with the merging of <Directory> in the parent-->child order, e.g., / is parent of /var that is parent of /var/www/
Each child will inherit from the parent the directives unless that directive is already present in the child. Options follows their particular scheme (see Apache guide). <Directory> inside a <VirtualHost> are evaluated only after the general config, allowing them to override previously declared <Directory>. At the end print in json format the apache configuration, see example below.
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


EXAMPLES = '''
"clara_apache_configuration": {
        "@": "server_config",                   -----> here we are in the global configuration of apache
        "AccessFileName": ".htaccess",
        "AddHandler": "type-map var",
        "AddOutputFilter": "INCLUDES .shtml",
        "SSLProtocol": [                        -----> in case the same directive is declared several times (in the same section) it is printed in reading order as a list
                    "-all +TLSv1.2",
                    "-all +TLSv1 +TLSv1.1 +TLSv1.2"
                ],
        "VirtualHost": [
            {
                "@": "*:443",                   ----> which virtual host
                "Alias": [
                    "/media \"/srv/www/\"", 
                                    ], 
                "Directory": [                 -----> Directory have been merged, this means that what you see here are the final directives that apply
                    {
                        "@": "\"/srv/www/bla.bla.net/htdocs\"",    -----> which directory
                        "Allow": "from all", 
                        "AllowOverride": "All", 
                        "Options": "FollowSymLinks",
                        "Require": "all granted"
                    }
                ], 
                "DocumentRoot": "\"/srv/www/review.bla.bla/htdocs\"",
                "SSLCertificateFile": "/etc/apache2/ssl/example.crt",
                "SSLCertificateKeyFile": "/etc/apache2/ssl/example.key",
                "SSLEngine": "on",
                "SSLProtocol": [
                    "all",
                    "-all +TLSv1 +TLSv1.1 +TLSv1.2"
                ],
                "ServerAlias": "review.int.de.clara.net",
'''



