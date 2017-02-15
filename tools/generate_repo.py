""" repository files and addons.xml generator """

""" Modified by Rodrigo@XMBCHUB to zip plugins/repositories to a "zip" folder """
""" Modified by BartOtten: create a repository addon, skip folders without addon.xml, user config file """

""" This file is "as is", without any warranty whatsoever. Use as own risk """

import os
import re
import md5
import zipfile
import shutil
from xml.dom import minidom
import glob
import datetime
from ConfigParser import SafeConfigParser

class Generator:
    
    """
        Generates a new addons.xml file from each addons addon.xml file
        and a new addons.xml.md5 hash file. Must be run from a subdirectory (eg. _tools) of
        the checked-out repo. Only handles single depth folder structure.
    """
    
    def __init__( self ):
       
        """
        Load the configuration
        """
        self.config = SafeConfigParser()
        self.config.read('config.ini')
        
        self.gitcomment = "Update to version " + self.config.get('addon', 'version')
        self.isrevision = self.config.get('options', 'is_revision')
        self.resources_path = "src"        
        self.tools_path=os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__))))
        self.rev_path = self.tools_path + os.path.sep + "revision.txt"
        self.output_path=self.config.get('locations', 'output_path')
        
        # travel path one up
        os.chdir(os.path.abspath(os.path.join(self.tools_path, os.pardir)))
                
        # generate files
        self._pre_run()
        self._generate_repo_files()
        self._generate_addons_file()
        self._generate_md5_file(self.output_path + "addons.xml")
        self._generate_zip_files()        
        # notify user
        print "Finished updating addons xml, md5 files and zipping addons"
        self._post_run()
        
    def _update_submodules ( self ):
            
        # update submodules
        if os.path.isfile(".gitmodules"): 
            fsubmodules = open(".gitmodules", "r").read()
            lsubmodules = re.compile('\[submodule "(.+?)"\]').findall(fsubmodules)
            for submodule in lsubmodules:
                print "Update module - " + str(submodule)
                os.system('git submodule update --init --recursive --force --remote -- "' + submodule + '"')
                        
    def _push_to_git ( self ):
    
        print "GIT commit"
        # git commit
        os.system('git add --all')
        os.system('git commit -m "' + self.gitcomment + '"')
    
        print "GIT Push"
        # push data to git
        os.system('git push')
                
    def _pre_run ( self ):
    
        # update git
        print "GIT Pull"
        os.system('git pull')
        
        # current revision + 1        
        if os.path.isfile( self.rev_path ): 
            self.revision = int(open(self.rev_path, "r").read()) + 1
        else:
            self.revision = 1

        if self.revision > 99:
            self.revision_str = str(self.revision)        
        elif self.revision <= 99 and self.revision > 9:        
            self.revision_str = "0" + str(self.revision)
        else:
            self.revision_str = "00" + str(self.revision)

        if self.isrevision == "true":                
            self.gitcomment = self.gitcomment + "." + self.revision_str
        else:
            self.gitcomment = self.gitcomment + " (" + self.revision_str + ")"
            
        print "########## " + self.gitcomment + " ##########"
        
        # update submodules
        self._update_submodules()
        
        # clear repos dir
        os.system("rm -rf " + self.output_path)
        
        # create output  path if it does not exists
        if not os.path.exists(self.output_path):
            os.makedirs(self.output_path)
            
    def _post_run ( self ):
    
        addonid=self.config.get('addon', 'id')
        os.system("rm -rf " + addonid)
        
        # save current revision + 1
        if os.path.isfile( self.rev_path ):
            os.remove(self.rev_path)
            
        self._save_file(str(self.revision), self.rev_path)
                    
        self._push_to_git()

    def _generate_repo_files ( self ):
        
        addonid=self.config.get('addon', 'id')
        name=self.config.get('addon', 'name')
        if self.isrevision == "true":
            version=self.config.get('addon', 'version') + "." + self.revision_str
        else:
            version=self.config.get('addon', 'version')        
        author=self.config.get('addon', 'author')
        kodi=self.config.get('addon', 'kodi')
        summary_en=self.config.get('addon', 'summary_en') 
        summary_ru=self.config.get('addon', 'summary_ru')
        description_en=self.config.get('addon', 'description_en')
        description_ru=self.config.get('addon', 'description_ru')
        news=self.config.get('addon', 'news')
        branch=self.config.get('locations', 'branch')
        url=self.config.get('locations', 'url')
        datadir=self.config.get('locations', 'datadir')
        compressed=self.config.get('options', 'compressed')
        zip=self.config.get('options', 'zip')
        hashes=self.config.get('options', 'hashes') 

        if os.path.isfile(addonid + os.path.sep + "addon.xml"):return
        
        print "Create repository addon"
        
        with open (self.tools_path + os.path.sep + "template.xml", "r") as template:
            template_xml=template.read()
        
        repo_xml = template_xml.format(
            addonid=addonid,
            name=name,
            version=version,
            author=author,
            kodi=kodi,
            summary_en=summary_en,
            summary_ru=summary_ru,
            description_en=description_en,
            description_ru=description_ru,
            news=news,
            branch=branch,
            url=url,
            datadir=datadir,
            compressed=compressed,
            zip=zip,            
            hashes=hashes,
            output_path=self.output_path)
            
        if os.path.exists(self.resources_path):
            shutil.copytree(os.path.abspath(self.resources_path), os.path.abspath(addonid))
            
        # save file
        if not os.path.exists(addonid):
            os.makedirs(addonid)
            
        self._save_file( repo_xml, file=addonid + os.path.sep + "addon.xml" )
                        
    def _generate_zip_files ( self ):
        addons = os.listdir( "." )
        # loop thru and add each addons addon.xml file
        for addon in addons:
            # create path
            _path = os.path.join( addon, "addon.xml" )
                       
            #skip path if it has no addon.xml
            if not os.path.isfile( _path ): continue       
            try:
                # skip any file or .git folder
                if ( not os.path.isdir( addon ) or addon == ".git" or addon == self.output_path or addon == self.tools_path): continue
                # create path
                _path = os.path.join( addon, "addon.xml" )
                # split lines for stripping
                document = minidom.parse(_path)
                addon_elements = document.getElementsByTagName("addon")
                for parent in addon_elements:
                    version = parent.getAttribute("version")
                    addonid = parent.getAttribute("id")
                                                                        
                self._generate_zip_file(addon, version, addonid)
                                
                self._copy_resources(addonid, document)
                    
            except Exception, e:
                print e

    def _generate_zip_file ( self, path, version, addonid):
        print "Generate zip file for " + addonid + " " + version
        filename = path + "-" + version + ".zip"
        try:
            zip = zipfile.ZipFile(filename, 'w')
            for root, dirs, files in os.walk(path + os.path.sep):
                for file in files:
                    if file == ".git" or file == ".gitignore" or file == "README.md": continue
                    zip.write(os.path.join(root, file))
                    
            zip.close()
         
            if not os.path.exists(self.output_path + addonid):
                os.makedirs(self.output_path + addonid)
         
            shutil.move(filename, self.output_path + addonid + os.path.sep + filename)
            
            zip_md5=self.config.get('options', 'zip_md5')
            
            if zip_md5 == "true":
                self._generate_md5_file(self.output_path + addonid + os.path.sep + filename)
            
        except Exception, e:
            print e

    def _generate_addons_file( self ):
        # addon list
        addons = os.listdir( "." )
        # final addons text
        addons_xml = u"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<addons>\n"
        # loop thru and add each addons addon.xml file
        for addon in addons:
            # create path
            _path = os.path.join( addon, "addon.xml" )
            #skip path if it has no addon.xml
            if not os.path.isfile( _path ): continue
            try:               
                # split lines for stripping
                xml_lines = open( _path, "r" ).read().splitlines()
                # new addon
                addon_xml = ""
                # loop thru cleaning each line
                for line in xml_lines:
                    # skip encoding format line
                    if ( line.find( "<?xml" ) >= 0 ): continue
                    # add line
                    addon_xml += unicode( line.rstrip() + "\n", "utf-8" )
                # we succeeded so add to our final addons.xml text
                addons_xml += addon_xml.rstrip() + "\n\n"
            except Exception, e:
                # missing or poorly formatted addon.xml
                print "Excluding %s for %s" % ( _path, e, )
        # clean and add closing tag
        addons_xml = addons_xml.strip() + u"\n</addons>\n"
        # save file
        self._save_file( addons_xml.encode( "utf-8" ), file=self.output_path + "addons.xml" )

    def _generate_md5_file( self, pfile ):
        try:
            # create a new md5 hash
            m = md5.new( open(pfile).read() ).hexdigest()
            # save file
            self._save_file( m, file=pfile + ".md5" )
        except Exception, e:
            # oops
            print "An error occurred creating addons.xml.md5 file!\n%s" % ( e, )

    def _save_file( self, data, file ):
        try:
            # write data to the file
            open( file, "w" ).write( data )
        except Exception, e:
            # oops
            print "An error occurred saving %s file!\n%s" % ( file, e, )
            
    def _copy_resources( self, addonid, document):
    
        assets_elements = document.getElementsByTagName("assets")
    
        if len(assets_elements)>0:
        
            for parent in assets_elements:
                for node in parent.childNodes:
                    res_patch = node.toxml().replace('<icon>','').replace('</icon>','').replace('<fanart>','').replace('</fanart>','').replace('<screenshot>','').replace('</screenshot>','').strip()
                    if res_patch != "":
                        src_patch = os.path.join( addonid, res_patch )
                        dst_patch = os.path.join(os.path.join( self.output_path, addonid ), res_patch)
                        #dst_patch = os.path.join(os.path.join( self.output_path, addonid ), os.path.basename(res_patch))
                        if os.path.isfile( src_patch ):
                            if not os.path.exists(os.path.dirname(dst_patch)):
                                os.makedirs(os.path.dirname(dst_patch))
                            shutil.copyfile(src_patch, dst_patch)
                     
        else:
        
            icon = os.path.join( addonid, "icon.png" )
            fanart = os.path.join( addonid, "fanart.jpg" )                
            res_path = os.path.join( self.output_path, addonid )
            
            if os.path.isfile( icon ):
                shutil.copyfile(icon, os.path.join(res_path, "icon.png"))
            if os.path.isfile( fanart ):
                shutil.copyfile(fanart, os.path.join(res_path,"fanart.jpg"))
            
if ( __name__ == "__main__" ):
    # start
    Generator()