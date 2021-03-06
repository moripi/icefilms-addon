#!/usr/bin/python

#Icefilms.info v1.1.0 Draft - anarchintosh / daledude / WestCoast13 19/3/2011

#All code Copyleft (GNU GPL v2) Anarchintosh and icefilms-xbmc team

# Still to-do (Low/Normal/High priority): 
#    - (N) better search results (maybe diff results for movies, tv shows & episodes) 
#    - (N) refresh for episodes & seasons
#    - (H) decide on final db schema (maybe keep ice url as PrimaryKey on all tables)
#    - (L) trailer search by youtube api
#    - (H) because tvdb is pretty slow, sometimes a network error happens
#    - (L) Quiet download. Have already tried with AddonScan 
#          in back & it works although sometimes it hangs. Needs proper testing.
#    - (L) Automatically watched status 
#    - (H) Create metacontainer with data for everything 
#          BUT need to decide about db first
#    - (H) fix the right path for the db
# Quite convoluted code. Needs a good cleanup.

#standard module imports
import sys,os
import time,re
import urllib,urllib2,cookielib,base64
import unicodedata

#necessary so that the metacontainers.py can use the scrapers
try: import xbmc,xbmcplugin,xbmcgui,xbmcaddon
except:
     xbmc_imported = False
else:
     xbmc_imported = True

# global constants
USER_AGENT = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3'
ICEFILMS_REFERRER = 'http://www.icefilms.info'

#get path to me
icepath=os.getcwd()

#append lib directory
sys.path.append( os.path.join( icepath, 'resources', 'lib' ) )

#imports of things bundled in the addon
import container_urls,clean_dirs,htmlcleaner,megaroutines
from metautils import metahandlers, metacontainers
from cleaners import *
from xgoogle.BeautifulSoup import BeautifulSoup,BeautifulStoneSoup
from xgoogle.search import GoogleSearch

def xbmcpath(path,filename):
     translatedpath = os.path.join(xbmc.translatePath( path ), ''+filename+'')
     return translatedpath
       
def Notify(typeq,title,message,times):
     #simplified way to call notifications. common notifications here.
     if title == '':
          title='Icefilms Notification'
     if typeq == 'small':
          if times == '':
               times='5000'
          smallicon=handle_file('smallicon')
          xbmc.executebuiltin("XBMC.Notification("+title+","+message+","+times+","+smallicon+")")
     if typeq == 'big':
          dialog = xbmcgui.Dialog()
          dialog.ok(' '+title+' ', ' '+message+' ')
     if typeq == 'megaalert1':
          ip = xbmc.getIPAddress()
          title='Megaupload Alert for IP '+ip
          message="Either you've reached your daily download limit\n or your IP is already downloading a file."
          dialog = xbmcgui.Dialog()
          dialog.ok(' '+title+' ', ' '+message+' ')
     if typeq == 'megaalert2':
          ip = xbmc.getIPAddress()
          title='Megaupload Info for IP '+ip
          message="No problems! You have not reached your limit."
          dialog = xbmcgui.Dialog()
          dialog.ok(' '+title+' ', ' '+message+' ')

#paths etc need sorting out.
icedatapath = 'special://profile/addon_data/plugin.video.icefilms'
metapath = icedatapath+'/mirror_page_meta_cache'
downinfopath = icedatapath+'/downloadinfologs'
transdowninfopath = xbmcpath(downinfopath,'')
transmetapath = xbmcpath(metapath,'')
translatedicedatapath = xbmcpath(icedatapath,'')
art = icepath+'/resources/art'

def handle_file(filename,getmode=''):
    #bad python code to add a get file routine.
    if filename == 'captcha':
        return_file = xbmcpath(icedatapath,'CaptchaChallenge.txt')
    elif filename == 'mirror':
        return_file = xbmcpath(icedatapath,'MirrorPageSource.txt')
    elif filename == 'episodesrc':
        return_file = xbmcpath(icedatapath,'EpisodePageSource.txt')
    elif filename == 'pageurl':
        return_file = xbmcpath(icedatapath,'PageURL.txt')
    
    elif filename == 'mediapath':
        return_file = xbmcpath(downinfopath,'MediaPath.txt')
    #extra thing to provide show name with year if going via episode list.
    elif filename == 'mediatvshowname':
        return_file = xbmcpath(downinfopath,'TVShowName.txt')
    #extra thing to provide season name.
    elif filename == 'mediatvseasonname':
        return_file = xbmcpath(downinfopath,'TVSeasonName.txt')
    
    elif filename == 'videoname':
        return_file = xbmcpath(metapath,'VideoName.txt')
    elif filename == 'sourcename':
        return_file = xbmcpath(metapath,'SourceName.txt')
    elif filename == 'description':
        return_file = xbmcpath(metapath,'Description.txt')
    elif filename == 'poster':
        return_file = xbmcpath(metapath,'Poster.txt')
    elif filename == 'mpaa':
        return_file = xbmcpath(metapath,'mpaa.txt')
    elif filename == 'listpic':
        return_file = xbmcpath(metapath,'listpic.txt')
    
    elif filename == 'smallicon':
        return_file = xbmcpath(art,'smalltransparent2.png')
    elif filename == 'homepage':
        return_file = xbmcpath(art,'homepage.png')
    elif filename == 'movies':
        return_file = xbmcpath(art,'movies.png')
    elif filename == 'music':
        return_file = xbmcpath(art,'music.png')
    elif filename == 'tvshows':
        return_file = xbmcpath(art,'tvshows.png')
    elif filename == 'movies_fav':
        return_file = xbmcpath(art,'movies_fav.png')
    elif filename == 'tvshows_fav':
        return_file = xbmcpath(art,'tvshows_fav.png')
    elif filename == 'other':
        return_file = xbmcpath(art,'other.png')
    elif filename == 'search':
        return_file = xbmcpath(art,'search.png')
    elif filename == 'standup':
        return_file = xbmcpath(art,'standup.png')
    elif filename == 'megapic':
        return_file = xbmcpath(art,'megaupload.png')
    elif filename == 'shared2pic':
        return_file = xbmcpath(art,'2shared.png')
    elif filename == 'localpic':
        return_file = xbmcpath(art,'local_file.jpg')

    if getmode == '':
        return return_file
    if getmode == 'open':
        try:
            opened_return_file=openfile(return_file)
            return opened_return_file
        except:
            print 'opening failed'
     
#useful global strings:
iceurl = 'http://www.icefilms.info/'

def openfile(filename):
     fh = open(filename, 'r')
     contents=fh.read()
     fh.close()
     return contents

def save(filename,contents):  
     fh = open(filename, 'w')
     fh.write(contents)  
     fh.close()

def appendfile(filename,contents):  
     fh = open(filename, 'a')
     fh.write(contents)  
     fh.close()


def DLDirStartup(selfAddon):

  # Startup routines for handling and creating special download directory structure 
  SpecialDirs=selfAddon.getSetting('use-special-structure')

  if SpecialDirs == 'true':
     mypath=str(selfAddon.getSetting('download-folder'))

     if mypath != '' or mypath is not None:
 
        if os.path.exists(mypath):
          initial_path=os.path.join(mypath,'Icefilms Downloaded Videos')
          tvpath=os.path.join(initial_path,'TV Shows')
          moviepath=os.path.join(initial_path,'Movies')

          tv_path_exists=os.path.exists(tvpath)
          movie_path_exists=os.path.exists(moviepath)

          if tv_path_exists == False or movie_path_exists == False:

            #IF BASE DIRECTORY STRUCTURE DOESN'T EXIST, CREATE IT
            #Also Add README files to TV Show and Movies direcories.
            #(readme files stops folders being deleted when running the DirCleaner)

            if tv_path_exists == False:
               os.makedirs(tvpath)
               tvreadme='Add this folder to your XBMC Library, and set it as TV to scan for metadata with TVDB.'
               tvreadmepath=os.path.join(tvpath,'README.txt')
               save(tvreadmepath,tvreadme)

            if movie_path_exists == False:
               os.makedirs(moviepath)
               moviereadme='Add this folder to your XBMC Library, and set it as Movies to scan for metadata with TheMovieDB.'
               moviereadmepath=os.path.join(moviepath,'README.txt')
               save(moviereadmepath,moviereadme)

          else:
              #IF DIRECTORIES EXIST, CLEAN DIRECTORY STRUCTURE (REMOVE EMPTY DIRECTORIES)
               clean_dirs.do_clean(tvpath)
               clean_dirs.do_clean(moviepath)


def LoginStartup(selfAddon):
     #Get whether user has set an account to use.
     Account = selfAddon.getSetting('megaupload-account')

     mu=megaroutines.megaupload(translatedicedatapath)

     #delete old logins
     mu.delete_login()
     
     if Account == 'false':
          print 'Account: '+'no account set'

     elif Account == 'true':
          #check for megaupload login and do it
          
          megauser = selfAddon.getSetting('megaupload-username')
          megapass = selfAddon.getSetting('megaupload-password')

          login=mu.set_login(megauser,megapass)
                   
          if megapass != '' and megauser != '':
               if login is False:
                    print 'Account: '+'login failed'
                    Notify('big','Megaupload','Login failed. Megaupload will load with no account.','')
               elif login is True:
                    print 'Account: '+'login succeeded'
                    HideSuccessfulLogin = selfAddon.getSetting('hide-successful-login-messages')
                    if HideSuccessfulLogin == 'false':
                         Notify('small','Megaupload', 'Account login successful.','')
                         
          if megapass == '' or megauser == '':
               print 'no login details specified, using no account'
               Notify('big','Megaupload','Login failed. Megaupload will load with no account.','')
                                
def ContainerStartup(selfAddon):

     #delete zips from the 'downloaded meta zips' dir that have equivalent text files.
     #have to do this at startup because it is not possible to delete the original file
     #after extracting, because the file is extracted by a built in xbmc function not python
     # (python won't wait until file has finished extracting before going on to run next lines)

     #define dl directory
     dlzips=os.path.join(translatedicedatapath,'downloaded meta zips')
               
     try:
          thefiles=os.listdir(dlzips)
          for thefile in thefiles:
               filestring=str(thefile)
               if filestring.endswith('.txt'):
                    filestring=re.sub('.txt','.zip',filestring)
                    os.remove(os.path.join(dlzips,filestring))
     except:
          print 'could not delete original file!'
     else:
          print 'deleted unnecessary zip.'

     metapath=os.path.join(translatedicedatapath,'meta_caches')

     #delete the meta folder if there are no covers. (cleanup failed installs)
     if os.path.exists(metapath):
          if not os.path.exists(os.path.join(metapath,'themoviedb','covers','tt0011130')):
               import shutil
               try:
                    shutil.rmtree(metapath)
               except:
                    print 'Failed to delete meta folder'
                    return False

                        
     #Quick hack for v1.0.0 --- only run if meta_caches does not exist
     if not os.path.exists(metapath):

          #get containers dict from container_urls.py
          containers = container_urls.get()
          
          #Offer to download the metadata
     
          dialog = xbmcgui.Dialog()
          ret = dialog.yesno('Download Meta Containers '+str(containers['date'])+' ?', 'There is a metadata container avaliable.','Install it to get images and info for videos.', 'Would you like to get it? Its a large '+str(containers['mv_db_base_size'])+'MB download.','Remind me later', 'Install')
          if ret==True:
                 
               #download dem files
               get_db_zip=Zip_DL_and_Install(containers['mv_db_url'],'movie','database')
               get_cover_zip=Zip_DL_and_Install(containers['mv_covers_url'],'movie','covers')

               #do nice notification
               if get_db_zip==True and get_cover_zip==True:
                    Notify('small','Metacontainer Installation Success','','')
               elif get_db_zip==False or get_cover_zip==False:
                    Notify('small','Metacontainer Installation Failure','','')


def Zip_DL_and_Install(url,dbtype,installtype):
               ####function to download and install a metacontainer. ####
     
               url = str(url)

               #define dl directory
               dlzips=os.path.join(translatedicedatapath,'downloaded meta zips')

               #get the download url
               mu=megaroutines.megaupload(translatedicedatapath)
               print 'URL:',url
               thefile=mu.resolve_megaup(url)

               #define the path to save it to
               filepath=os.path.normpath(os.path.join(dlzips,thefile[1]))
          
               print 'FILEPATH: ',filepath
               filepath_exists=os.path.exists(filepath)
               #if zip does not already exist, download from url, with nice display name.
               if filepath_exists==False:

                    do_wait(thefile[3])
                    
                    print 'downloading zip'
                    
                    Download(thefile[0],filepath,dbtype+' '+installtype)

                    #make a text file with the same name as zip, to act as a very simple download log.
                    textfile=re.sub('.zip','',thefile[1])
                    textfilepath=os.path.join(dlzips,textfile+'.txt')
                    save(textfilepath,' ')
                    
               elif filepath_exists==True:
                    print 'zip already downloaded, attempting extraction'

               print '!!!!handling meta install!!!!'
               install=metacontainers.Install_Icefilms_Container(translatedicedatapath,filepath,dbtype,installtype)
               return install


def Startup_Routines(selfAddon):
     
     # avoid error on first run if no paths exists, by creating paths
     if not os.path.exists(translatedicedatapath): os.makedirs(translatedicedatapath)
     if not os.path.exists(transmetapath): os.makedirs(transmetapath)
     if not os.path.exists(transdowninfopath): os.makedirs(transdowninfopath)

     dlzips=os.path.join(translatedicedatapath,'downloaded meta zips')
     if not os.path.exists(dlzips): os.makedirs(dlzips)
          
     #force refresh addon repositories, to check for updates.
     #xbmc.executebuiltin('UpdateAddonRepos')
     
     # Run the startup routines for special download directory structure 
     DLDirStartup(selfAddon)

     # Run the login startup routines
     LoginStartup(selfAddon)

     # Run the container checking startup routines, if enable meta is set to true
     EnableMeta = selfAddon.getSetting('use-meta')
     if EnableMeta=='true': ContainerStartup(selfAddon)

def CATEGORIES():  #  (homescreen of addon)
          #get settings
          selfAddon = xbmcaddon.Addon(id='plugin.video.icefilms')

          #run startup stuff
          Startup_Routines(selfAddon)
          print 'Homescreen'

          #get necessary paths
          homepage=handle_file('homepage','')
          tvshows=handle_file('tvshows','')
          movies=handle_file('movies','')
          music=handle_file('music','')
          standup=handle_file('standup','')
          other=handle_file('other','')
          search=handle_file('search','')

          #add directories
          HideHomepage = selfAddon.getSetting('hide-homepage')
          
          addDir('TV Shows',iceurl+'tv/a-z/1',50,tvshows)
          addDir('Movies',iceurl+'movies/a-z/1',51,movies)
          addDir('Music',iceurl+'music/a-z/1',52,music)
          addDir('Stand Up Comedy',iceurl+'standup/a-z/1',53,standup)
          addDir('Other',iceurl+'other/a-z/1',54,other)
          if HideHomepage == 'false':
                addDir('Homepage',iceurl+'index',56,homepage)
          addDir('Favourites',iceurl,57,os.path.join(art,'favourites.png'))
          addDir('Search',iceurl,55,search)


def prepare_list(directory,dircontents):
     #create new empty list
     stringList = []

     #Open all files in dir
     for thefile in dircontents:
          try:
               filecontents=openfile(os.path.join(directory,thefile))

               #add this to list
               stringList.append(filecontents)
                              
          except:
               print 'problem with opening a favourites item'

     #sort list alphabetically and return it.
     tupleList = [(x.lower(), x) for x in stringList]

     #wesaada's patch for ignoring The etc when sorting favourites list.
     articles = ("a","an","the")
     tupleList.sort(key=lambda s: tuple(word for word in s[1].split() if word.lower() not in articles))

     return [x[1] for x in tupleList]

def favRead(string):
     try:
          splitter=re.split('\|+', string)
          name=splitter[0]
          url=splitter[1]
          mode=int(splitter[2])
          try:
               imdb_id=str(splitter[3])
          except:
               imdb_id=''
     except:
          return None
     else:
          return name,url,mode,imdb_id

def addFavourites(enablemetadata,directory,dircontents,contentType):
    #get the strings of data from the files, and return them alphabetically
    stringlist=prepare_list(directory,dircontents)
    
    if enablemetadata == True:
        metaget=metahandlers.MetaData(translatedicedatapath)
         
    #for each string
    for thestring in stringlist:
    
        #split it into its component parts
        info = favRead(thestring)
        if info is not None:
        
            if enablemetadata == True:
                #return the metadata dictionary
                if info[3] is not None:
                    
                    # get the ice_id from url, usefull for searches & homepage
                    if contentType == 'tvshow':
                        ice_id=str(info[1]).replace('http://www.icefilms.info/tv/series/','')
                    elif contentType == 'movie':
                        ice_id=str(info[1]).replace('http://www.icefilms.info/ip.php?v=','')
                    else:
                        ice_id = ''
                        print 'ice id not found in url->' + info[1]
                    print ice_id
                    
                    #return the metadata dictionary
                    meta=metaget.get_meta(info[3], contentType, info[0], ice_id)
                    
                    if meta is None:
                        #add all the items without meta
                        addDir(info[0],info[1],info[2],'',delfromfav=True)
                    else:
                        #add directories with meta
                        addDir(info[0],info[1],info[2],'',metainfo=meta,delfromfav=True,imdb=info[3])        
                else:
                    #add all the items without meta
                    addDir(info[0],info[1],info[2],'',delfromfav=True)
            else:
                #add all the items without meta
                addDir(info[0],info[1],info[2],'',delfromfav=True)

     
def FAVOURITES(url):
    #Favourites folder.
    
    #get necessary paths
    tvshows=handle_file('tvshows_fav','')
    movies=handle_file('movies_fav','')
     
    addDir('TV Shows',iceurl,570,tvshows)
    addDir('Movies',iceurl,571,movies)

                         
def URL_TYPE(url):
     #Check whether url is a tv episode list or movie/mirrorpage
     if url.startswith(iceurl+'ip'):
               print 'url is a mirror page url'
               return 'mirrors'
     elif url.startswith(iceurl+'tv/series'):
               print 'url is a tv ep list url'
               return 'episodes'     

def METAFIXER(url):
     #Icefilms urls passed to me will have their proper names and imdb numbers returned.
     source=GetURL(url)

     url_type=URL_TYPE(url)

     #get proper name from the page. (in case it is a weird name)
     
     if url_type=='mirrors':
               #get imdb number.
               match=re.compile('<a class=iframe href=http://www.imdb.com/title/(.+?)/ ').findall(source)      

               #check if it is an episode. 
               epcheck=re.search('<a href=/tv/series/',source)

               #if it is, return the proper series name as opposed to the mirror page name.
               if epcheck is not None:
                    tvget=re.compile('<a href=/tv/series/(.+?)>').findall(source)
                    tvurl=iceurl+'tv/series/'+str(tvget[0])
                    #load ep page and get name from that. sorry icefilms bandwidth!
                    tvsource=GetURL(tvurl)
                    name=re.compile('<h1>(.+?)<a class').findall(tvsource)

               #return mirror page name.
               if epcheck is None:
                    name=re.compile('''<span style="font-size:large;color:white;">(.+?)</span>''').findall(source)
                    
               name=CLEANUP(name[0])
               return name,match[0]

     elif url_type=='episodes':
               #TV
               name=re.compile('<h1>(.+?)<a class').findall(source)
               match=re.compile('href="http://www.imdb.com/title/(.+?)/"').findall(source)
               name=CLEANUP(name[0])
               return name,match[0]
     
     
def ADD_TO_FAVOURITES(name,url,imdbnum):
    #Creates a new text file in favourites folder. The text file is named after the items name, and contains the name, url and relevant mode.
    
    if name is not None and url is not None:
    
        #Set favourites path, and create it if it doesn't exist.
        favpath=os.path.join(translatedicedatapath,'Favourites')
        tvfav=os.path.join(favpath,'TV')
        moviefav=os.path.join(favpath,'Movies')
        
        try:
            os.makedirs(tvfav)
        except:
            pass
        try:
            os.makedirs(moviefav)
        except:
            pass
        
        #Check what kind of url it is and set themode and savepath (helpful for metadata) accordingly
        
        
        #fix name and imdb number for Episode List entries in Search.
        if imdbnum == 'nothing':
            metafix=METAFIXER(url)
            name=metafix[0]
            imdbnum=metafix[1]
        
        
        url_type=URL_TYPE(url)
        
        if url_type=='mirrors':
            themode='100'
            savepath=moviefav
             
        elif url_type=='episodes':
            themode='12'
            savepath=tvfav
        
        print 'NAME:',name,'URL:',url,'IMDB NUMBER:',imdbnum
        
        #Delete HD entry from filename. using name as filename makes favourites appear alphabetically.
        adjustedname=cleanFilename( re.sub(' *HD*','', name) )
        
        #encode the filename to the safe string *** to check ***
        #adjustedname=base64.urlsafe_b64encode(name)
        
        #Save the new favourite if it does not exist.
        NewFavFile=os.path.join(savepath,adjustedname+'.txt')
        if not os.path.exists(NewFavFile):
        
            #Use | as separators that can be used by re.split when reading favourites folder.
            favcontents=name+'|'+url+'|'+themode+'|'+imdbnum
            save(NewFavFile,favcontents)
        else:
            print 'favourite already exists'
    
    else:
        print 'name or url is none:'
        print 'NAME: ',name
        print 'URL: ',url


     
def DELETE_FROM_FAVOURITES(name,url):
    #Deletes HD entry from filename
    name=cleanFilename( re.sub(' *HD*','', name) )
    #encode the filename to the safe string *** to check ***
    #name=base64.urlsafe_b64encode(name)
    
    favpath=os.path.join(translatedicedatapath,'Favourites')
    
    url_type=URL_TYPE(url)
    
    if url_type=='mirrors':
         itempath=os.path.join(favpath,'Movies',name+'.txt')
    
    elif url_type=='episodes':
         itempath=os.path.join(favpath,'TV',name+'.txt')
    
    if os.path.exists(itempath):
         os.remove(itempath)

def CLEAR_FAVOURITES(url):
     
     dialog = xbmcgui.Dialog()
     ret = dialog.yesno('WARNING!', 'Delete all your favourites?','','','Cancel','Go Nuclear')
     if ret==True:
          import shutil
          favpath=os.path.join(translatedicedatapath,'Favourites')
          tvfav=os.path.join(favpath,'TV')
          moviefav=os.path.join(favpath,'Movies')
          try:
               shutil.rmtree(tvfav)
          except:
               pass
          try:
               shutil.rmtree(moviefav)
          except:
               pass

def ICEHOMEPAGE(url):
        addDir('Recently Added',iceurl+'index',60,os.path.join(art,'recently added.png'))
        addDir('Latest Releases',iceurl+'index',61,os.path.join(art,'latest releases.png'))
        addDir('Being Watched Now',iceurl+'index',62,os.path.join(art,'being watched now.png'))

        #delete tv show name file
        tvshowname=handle_file('mediatvshowname','')
        try:
               os.remove(tvshowname)
        except:
               pass

def RECENT(url):
        link=GetURL(url)
        homepage=re.compile('<h1>Recently Added</h1>(.+?)<h1>Statistics</h1>').findall(link)
        for scrape in homepage:
                scrape='<h1>Recently Added</h1>'+scrape+'<h1>Statistics</h1>'
                recadd=re.compile('<h1>Recently Added</h1>(.+?)<h1>Latest Releases</h1>').findall(scrape)
                for scraped in recadd:
                        mirlinks=re.compile('<a href=(.+?)>(.+?)</a>').findall(scraped)
                        for url,name in mirlinks:
                                url='http://www.icefilms.info'+url
                                name=CLEANUP(name)
                                addDir(name,url,100,'',disablefav=True)
    
def LATEST(url):
        link=GetURL(url)
        homepage=re.compile('<h1>Recently Added</h1>(.+?)<h1>Statistics</h1>').findall(link)
        for scrape in homepage:
                scrape='<h1>Recently Added</h1>'+scrape+'<h1>Statistics</h1>'
                latrel=re.compile('<h1>Latest Releases</h1>(.+?)<h1>Being Watched Now</h1>').findall(scrape)
                for scraped in latrel:
                        mirlinks=re.compile('<a href=(.+?)>(.+?)</a>').findall(scraped)
                        for url,name in mirlinks:
                                url='http://www.icefilms.info'+url
                                name=CLEANUP(name)
                                addDir(name,url,100,'',disablefav=True)

def WATCHINGNOW(url):
        link=GetURL(url)
        homepage=re.compile('<h1>Recently Added</h1>(.+?)<h1>Statistics</h1>').findall(link)
        for scrape in homepage:
                scrapy='<h1>Recently Added</h1>'+scrape+'<h1>Statistics</h1>'
                watnow=re.compile('<h1>Being Watched Now</h1>(.+?)<h1>Statistics</h1>').findall(scrapy)
                for scraped in watnow:
                        mirlinks=re.compile('href=(.+?)>(.+?)</a>').findall(scraped)
                        for url,name in mirlinks:
                                url='http://www.icefilms.info'+url
                                name=CLEANUP(name)
                                addDir(name,url,100,'',disablefav=True)    

def SEARCH(url):
    kb = xbmc.Keyboard('', 'Search Icefilms.info', False)
    kb.doModal()
    if (kb.isConfirmed()):
        search = kb.getText()
        if search != '':
            tvshowname=handle_file('mediatvshowname','')
            seasonname=handle_file('mediatvseasonname','')
            DoEpListSearch(search)
            DoSearch(search,0)
            DoSearch(search,1)
            DoSearch(search,2)
            
            # Enable library mode & set the right view for the content
            setView('movies', 'movies-view')
            
            #delete tv show name file, do the same for season name file
            try:
                os.remove(tvshowname)
            except:
                pass
            try:
                os.remove(seasonname)
            except:
                pass
               
                               
def DoSearch(search,page):        
        gs = GoogleSearch('site:http://www.icefilms.info/ip '+search+'')
        gs.results_per_page = 25
        gs.page = page
        results = gs.get_results()
        find_meta_for_search_results(results, 100)

def DoEpListSearch(search):
        tvurl='http://www.icefilms.info/tv/series'              
        
        # use urllib.quote_plus() on search instead of re.sub ?
        searcher=urllib.quote_plus(search)
        #searcher=re.sub(' ','+',search)
        url='http://www.google.com/search?hl=en&q=site:'+tvurl+'+'+searcher+'&btnG=Search&aq=f&aqi=&aql=&oq='
        link=GetURL(url)
        
        match=re.compile('<h3 class="r"><a href="'+tvurl+'(.+?)"(.+?)">(.+?)</h3>').findall(link)
        find_meta_for_search_results(match, 12, search)


def TVCATEGORIES(url):
        caturl = iceurl+'tv/'        
        setmode = '11'
        addDir('A-Z Directories',caturl+'a-z/1',10,os.path.join(art,'az directories.png'))            
        ADDITIONALCATS(setmode,caturl)
        
def MOVIECATEGORIES(url):
        caturl = iceurl+'movies/'        
        setmode = '2'
        addDir('A-Z Directories',caturl+'a-z/1',1,os.path.join(art,'az directories.png'))
        ADDITIONALCATS(setmode,caturl)
        
def MUSICCATEGORIES(url):
        caturl = iceurl+'music/'        
        setmode = '2'
        addDir('A-Z List',caturl+'a-z/1',setmode,os.path.join(art,'az lists.png'))
        ADDITIONALCATS(setmode,caturl)

def STANDUPCATEGORIES(url):
        caturl = iceurl+'standup/'        
        setmode = '2'
        addDir('A-Z List',caturl+'a-z/1',setmode,os.path.join(art,'az lists.png'))
        ADDITIONALCATS(setmode,caturl)

def OTHERCATEGORIES(url):
        caturl = iceurl+'other/'        
        setmode = '2'
        addDir('A-Z List',caturl+'a-z/1',setmode,os.path.join(art,'az lists.png'))
        ADDITIONALCATS(setmode,caturl)

def ADDITIONALCATS(setmode,caturl):
        if caturl == iceurl+'movies/':
             addDir('HD 720p',caturl,63,os.path.join(art,'HD 720p.png'))
        PopRatLat(setmode,caturl,'1')
        addDir('Genres',caturl,64,os.path.join(art,'genres.png'))

def PopRatLat(modeset,caturl,genre):
        if caturl == iceurl+'tv/':
             setmode = '11'
        else:
             setmode = '2'
        addDir('Popular',caturl+'popular/'+genre,setmode,os.path.join(art,'popular.png'))
        addDir('Highly Rated',caturl+'rating/'+genre,setmode,os.path.join(art,'highly rated.png'))
        addDir('Latest Releases',caturl+'release/'+genre,setmode,os.path.join(art,'latest releases.png'))
        addDir('Recently Added',caturl+'added/'+genre,setmode,os.path.join(art,'recently added.png'))

def HD720pCat(url):
        PopRatLat('2',url,'hd')

def Genres(url):
        addDir('Action',url,70,'')
        addDir('Animation',url,71,'')
        addDir('Comedy',url,72,'')
        addDir('Documentary',url,73,'')
        addDir('Drama',url,74,'')
        addDir('Family',url,75,'')
        addDir('Horror',url,76,'')
        addDir('Romance',url,77,'')
        addDir('Sci-Fi',url,78,'')
        addDir('Thriller',url,79,'')

def Action(url):
     PopRatLat('2',url,'action')

def Animation(url):
     PopRatLat('2',url,'animation')

def Comedy(url):
     PopRatLat('2',url,'comedy')

def Documentary(url):
     PopRatLat('2',url,'documentary')

def Drama(url):
     PopRatLat('2',url,'drama')

def Family(url):
     PopRatLat('2',url,'family')

def Horror(url):
     PopRatLat('2',url,'horror')

def Romance(url):
     PopRatLat('2',url,'romance')

def SciFi(url):
     PopRatLat('2',url,'sci-fi')

def Thriller(url):
     PopRatLat('2',url,'thriller')

def MOVIEA2ZDirectories(url):
        setmode = '2'
        caturl = iceurl+'movies/a-z/'
        
        #Generate A-Z list and add directories for all letters.
        A2Z=[chr(i) for i in xrange(ord('A'), ord('Z')+1)]

        if xbmc_imported:
             #Add number directory
             addDir ('#1234',caturl+'1',setmode,os.path.join(art,'letters','1.png'))
             for theletter in A2Z:
                  addDir (theletter,caturl+theletter,setmode,os.path.join(art,'letters',theletter+'.png'))
        else:
             print '### GETTING MOVIE METADATA FOR ALL *MUSIC* ENTRIES'
             MOVIEINDEX(iceurl+'music/a-z/1')
             print '### GETTING MOVIE METADATA FOR ALL *STANDUP* ENTRIES'
             MOVIEINDEX(iceurl+'standup/a-z/1')
             print '### GETTING MOVIE METADATA FOR ALL *OTHER* ENTRIES'
             MOVIEINDEX(iceurl+'other/a-z/1')
             print '### GETTING MOVIE METADATA FOR ALL ENTRIES ON: '+'1'
             MOVIEINDEX(caturl+'1')
             for theletter in A2Z:
                  print '### GETTING MOVIE METADATA FOR ALL ENTRIES ON: '+theletter
                  MOVIEINDEX(caturl+theletter)

def TVA2ZDirectories(url):
        setmode = '11'
        caturl = iceurl+'tv/a-z/'

        #Generate A-Z list and add directories for all letters.
        A2Z=[chr(i) for i in xrange(ord('A'), ord('Z')+1)]

        if xbmc_imported:
            #Add number directory
            addDir ('#1234',caturl+'1',setmode,os.path.join(art,'letters','1.png'))
            for theletter in A2Z:
                 addDir (theletter,caturl+theletter,setmode,os.path.join(art,'letters',theletter+'.png'))
        else:
            print '### GETTING TV METADATA FOR ALL ENTRIES ON: '+'1'
            TVINDEX(caturl+'1')
            for theletter in A2Z:
                 print '### GETTING TV METADATA FOR ALL ENTRIES ON: '+theletter
                 TVINDEX(caturl+theletter)

def MOVIEINDEX(url):
    #Indexer for most things. (Movies,Music,Stand-up etc) 
    
    link=GetURL(url)
    
    # we do this to fix the problem when there is no imdb_id. 
    # I have found only one movie with this problem, but we must check this...
    link = re.sub('<a name=i id=>','<a name=i id=None>',link)
    
    scrape=re.compile('<a name=i id=(.+?)></a><img class=star><a href=/(.+?)>(.+?)<br>').findall(link)
    getMeta(scrape, 100)
    
    # Enable library mode & set the right view for the content
    setView('movies', 'movies-view')

def TVINDEX(url):
    #Indexer for TV Shows only.

    link=GetURL(url)

    #list scraper now tries to get number of episodes on icefilms for show. this only works in A-Z.
    match=re.compile('<a name=i id=(.+?)></a><img class=star><a href=/(.+?)>(.+?)</a>(.+?)br>').findall(link)

    getMeta(match, 12)
    print 'TVindex loader'
    
    # Enable library mode & set the right view for the content
    setView('movies', 'tvshows-view')


def TVSEASONS(url, imdb_id):
# displays by seasons. pays attention to settings.
        #get settings
        selfAddon = xbmcaddon.Addon(id='plugin.video.icefilms')

        FlattenSingleSeasons = selfAddon.getSetting('flatten-single-season')
        source=GetURL(url)

        #Save the tv show name for use in special download directories.
        tvshowname=handle_file('mediatvshowname','')
        match=re.compile('<h1>(.+?)<a class').findall(source)
        save(tvshowname,match[0])

        # get and save the TV Show poster link
        try:
          imgcheck1 = re.search('<a class=img target=_blank href=', link)
          imgcheck2 = re.search('<iframe src=http://referer.us/f/\?url=', link)
          if imgcheck1 is not None:
               match4=re.compile('<a class=img target=_blank href=(.+?)>').findall(link)
               save(posterfile,match4[0])
          if imgcheck2 is not None:
               match5=re.compile('<iframe src=http://referer.us/f/\?url=(.+?) width=').findall(link)
               save(posterfile,match5[0])
        except:
          pass
        
        ep_list = str(BeautifulSoup(source).find("span", { "class" : "list" } ))

        season_list=re.compile('<h4>(.+?)</h4>').findall(ep_list)
        listlength=len(season_list)
        if listlength > 0:
            metaget=metahandlers.MetaData(translatedicedatapath)
            metas = metaget.getSeasonCover(imdb_id, season_list, refresh=False)
        num = 0
        for seasons in season_list:
            #print " Seasons are ->>>" + seasons 
            if FlattenSingleSeasons==True and listlength <= 1:             
            
                #proceed straight to adding episodes.
                TVEPISODES(seasons,source=ep_list,imdb_id=''+str(imdb_id))
            else:
                #save episode page source code
                save(handle_file('episodesrc'),ep_list)
                temp = metas[num]
                cover_url = temp['cover_url']
                print cover_url
                num = num + 1 
                #add season directories
                addDir(seasons,'',13,cover_url,imdb=''+str(imdb_id)) 


def TVEPISODES(name,url=None,source=None,imdb_id=None):
    #Save the season name for use in the special download directories.
    save(handle_file('mediatvseasonname'),name)
    print 'episodes url    --->' + str(url)
    print 'episodes source --->' + str(source)
    #If source was'nt passed to function, open the file it should be saved to.
    if source is None:
        source = openfile(handle_file('episodesrc'))
        
    #special hack to deal with annoying re problems when recieving brackets ( )
    if re.search('\(',name) is not None:
        name = str((re.split('\(+', name))[0])
        #name=str(name[0])
    
    #quick hack of source code to simplfy scraping.
    source=re.sub('</span>','<h4>',source)
    
    #get all the source under season heading.
    #Use .+?/h4> not .+?</h4> for The Daily Show et al to work.
    match=re.compile('<h4>'+name+'.+?/h4>(.+?)<h4>').findall(source)
    for seasonSRC in match:
        print "Season Source is " + name
        TVEPLINKS(seasonSRC, name, imdb_id)
             
def TVEPLINKS(source, season, imdb_id):
    
    # displays all episodes in the source it is passed.
    match=re.compile('<img class="star" /><a href="/(.+?)&amp;">(.+?)</a>').findall(source)
    for url,name in match:
            print " TVepLinks name " + name
            get_episode(season, name, imdb_id, url)
            #name=CLEANUP(name)
            #addDir(name,iceurl+url,100,'')    
    
    # Enable library mode & set the right view for the content
    setView('episodes', 'episodes-view')
             
def LOADMIRRORS(url):
     # This proceeds from the file page to the separate frame where the mirrors can be found,
     # then executes code to scrape the mirrors
     link=GetURL(url)
     #print link
     posterfile=handle_file('poster','')
     videonamefile=handle_file('videoname','')
     descriptionfile=handle_file('description','')
     mpaafile=handle_file('mpaa','')
     mediapathfile=handle_file('mediapath','')
     
     
     #---------------Begin phantom metadata getting--------

     #Save metadata on page to files, for use when playing.
     # Also used for creating the download directory structures.
     
     try:
          os.remove(posterurl)
     except:
          print 'posterurl does not exist'

     try:
          os.remove(mpaafile)
     except:
          print 'mpaafile does not exist'        
     

     # get and save videoname
     namematch=re.compile('''<span style="font-size:large;color:white;">(.+?)</span>''').findall(link)
     save(videonamefile,namematch[0])

     # get and save description
     match2=re.compile('<th>Description:</th><td>(.+?)<').findall(link)
     try:
          save(descriptionfile,match2[0])
     except:
          pass
     
     # get and save poster link
     try:
          imgcheck1 = re.search('<img width=250 src=', link)
          imgcheck2 = re.search('<iframe src=/noref.php\?url=', link)
          if imgcheck1 is not None:
               match4=re.compile('<img width=250 src=(.+?) style').findall(link)
               save(posterfile,match4[0])
          if imgcheck2 is not None:
               match5=re.compile('<iframe src=/noref.php\?url=(.+?) width=').findall(link)
               save(posterfile,match5[0])
     except:
          pass

     #get and save mpaa     
     mpaacheck = re.search('MPAA Rating:', link)         
     if mpaacheck is not None:     
          match4=re.compile('<th>MPAA Rating:</th><td>(.+?)</td>').findall(link)
          mpaa=re.sub('Rated ','',match4[0])
          try:
               save(mpaafile,mpaa)
          except:
               pass


     ########### get and save potential file path. This is for use in download function later on.
     epcheck1 = re.search('Episodes</a>', link)
     epcheck2 = re.search('Episode</a>', link)
     if epcheck1 is not None or epcheck2 is not None:
          shownamepath=handle_file('mediatvshowname','')
          if os.path.exists(shownamepath):
               #open media file if it exists, as that has show name with date.
               showname=openfile(shownamepath)
          else:
               #fall back to scraping show name without date from the page.
               print 'USING FALLBACK SHOW NAME'
               fallbackshowname=re.compile("alt\='Show series\: (.+?)'").findall(link)
               showname=fallbackshowname[0]
          try:
               #if season name file exists
               seasonnamepath=handle_file('mediatvseasonname','')
               if os.path.exists(seasonnamepath):
                    seasonname=openfile(seasonnamepath)
                    save(mediapathfile,'TV Shows/'+showname+'/'+seasonname)
               else:
                    save(mediapathfile,'TV Shows/'+showname)
          except:
               print "FAILED TO SAVE TV SHOW FILE PATH!"
     else:
          
          save(mediapathfile,'Movies/'+namematch[0])

     #---------------End phantom metadata getting stuff --------------

     match=re.compile('/membersonly/components/com_iceplayer/(.+?)" width=').findall(link)
     match[0]=re.sub('%29',')',match[0])
     match[0]=re.sub('%28','(',match[0])
     mirrorpageurl = iceurl+'membersonly/components/com_iceplayer/'+match[0]

     mlink=GetURL(mirrorpageurl)

     #check for recaptcha
     has_recaptcha = check_for_captcha(mlink)

     if has_recaptcha:
          RECAPTCHA(mirrorpageurl)
     else:
          GETMIRRORS(mirrorpageurl,mlink)

def check_for_captcha(source):
     #check for recaptcha in the page source, and return true or false.
     has_recaptcha = re.search('recaptcha_challenge_field', source)

     if has_recaptcha is None:
          return False
     else:
          return True

def RECAPTCHA(url):
     print 'initiating recaptcha passthrough'
     source = GetURL(url)
     match = re.compile('<iframe src="http://www.google.com/recaptcha/api/noscript\?k\=(.+?)" height').findall(source)
     for token in match:
          surl = 'http://www.google.com/recaptcha/api/challenge?k=' + token
     tokenlink=GetURL(surl)
     matchy=re.compile("challenge : '(.+?)'").findall(tokenlink)
     for challenge in matchy:
          imageurl='http://www.google.com/recaptcha/api/image?c='+challenge

     captchafile=handle_file('captcha','')
     pageurlfile=handle_file('pageurl','')

     #hacky method --- save all captcha details and mirrorpageurl to file, to reopen in next step
     save(captchafile, challenge)
     save(pageurlfile, url)

     #addDir uses imageurl as url, to avoid xbmc displaying old cached image as the fresh captcha
     addDir('Enter Captcha - Type the letters',imageurl,99,imageurl)

def CAPTCHAENTER(surl):
     url=handle_file('pageurl','open')
     kb = xbmc.Keyboard('', 'Type the letters in the captcha image', False)
     kb.doModal()
     if (kb.isConfirmed()):
          userInput = kb.getText()
          if userInput != '':
               challengeToken=handle_file('captcha','open')
               print 'challenge token: '+challengeToken
               parameters = urllib.urlencode({'recaptcha_challenge_field': challengeToken, 'recaptcha_response_field': userInput})
               source = GetURL(url, parameters)
               has_recaptcha = check_for_captcha(source)
               if has_recaptcha:
                    Notify('big', 'Text does not match captcha image!', 'To try again, close this box and then: \n Press backspace twice, and reselect your video.', '')
               else:
                    GETMIRRORS(url,source)
          elif userInput == '':
               Notify('big', 'No text entered!', 'To try again, close this box and then: \n Press backspace twice, and reselect your video.', '')               

def GETMIRRORS(url,link):
# This scrapes the megaupload mirrors from the separate url used for the video frame.
# It also displays them in an informative fashion to user.
# Displays in three directory levels: HD / DVDRip etc , Source, PART

    #get settings
    selfAddon = xbmcaddon.Addon(id='plugin.video.icefilms')
         
    #hacky method -- save page source to file
    mirrorfile=handle_file('mirror','')
    save(mirrorfile, link)
    
    #check for the existence of categories, and set values.
    if re.search('<div class=ripdiv><b>DVDRip / Standard Def</b>', link) is not None: dvdrip = 1
    else: dvdrip = 0
    
    if re.search('<div class=ripdiv><b>HD 720p</b>', link) is not None: hd720p = 1
    else: hd720p = 0
    
    if re.search('<div class=ripdiv><b>DVD Screener</b>', link) is not None: dvdscreener = 1
    else: dvdscreener = 0
    
    if re.search('<div class=ripdiv><b>R5/R6 DVDRip</b>', link) is not None: r5r6 = 1
    else: r5r6 = 0
    
    FlattenSrcType = selfAddon.getSetting('flatten-source-type')        
     
    # Search if there is a local version of the file
    #get proper name of vid
    vidname=handle_file('videoname','open')
    mypath=Get_Path(name,vidname)
    print 'MYPATH: ',mypath
    if mypath != 'path not set':
        if os.path.isfile(mypath) is True:
            localpic=handle_file('localpic','')
            addExecute('Source    | Local | Full',mypath,205,localpic)
    
    #only detect and proceed directly to adding sources if flatten sources setting is true
    if FlattenSrcType == 'true':
    
         #add up total number of categories.
         total = dvdrip + hd720p + dvdscreener + r5r6
    
         #if there is only one category, skip to adding sources.
         if total == 1:
              if dvdrip == 1:
                   DVDRip(url)
              elif hd720p == 1:
                   HD720p(url)
              elif dvdscreener == 1:
                   DVDScreener(url)
              elif r5r6 == 1:
                   R5R6(url)
    
         #if there are multiple categories, add sub directories.
         elif total > 1:
              addCatDir(url,dvdrip,hd720p,dvdscreener,r5r6)
    
    #if flattensources is set to false, don't flatten                
    elif FlattenSrcType == 'false':
         addCatDir(url,dvdrip,hd720p,dvdscreener,r5r6)


                
def addCatDir(url,dvdrip,hd720p,dvdscreener,r5r6):
        if dvdrip == 1:
                addDir('DVDRip',url,101,os.path.join(art,'source_types','dvd.png'))
        if hd720p == 1:
                addDir('HD 720p',url,102,os.path.join(art,'source_types','hd720p.png'))
        if dvdscreener == 1:
                addDir('DVD Screener',url,103,os.path.join(art,'source_types','dvdscreener.png'))
        if r5r6 == 1:
                addDir('R5/R6 DVDRip',url,104,os.path.join(art,'source_types','r5r6.png')) 

def Add_Multi_Parts(name,url,icon):
     #StackMulti = selfAddon.getSetting('stack-multi-part')
     #StackMulti=='false'
     #if StackMulti=='true':
     #save list of urls to later be stacked when user selects part
          addExecute(name,url,200,icon)

     #elif StackMulti=='false':
     #     addExecute(name,url,200,icon)



def PART(scrap,sourcenumber,hide2shared,megapic,shared2pic):
     #check if source exists
     sourcestring='Source #'+sourcenumber
     checkforsource = re.search(sourcestring, scrap)
     
     #if source exists proceed.
     if checkforsource is not None:
          #print 'Source #'+sourcenumber+' exists'
          
          #check if source contains multiple parts
          multiple_part = re.search('<p>Source #'+sourcenumber+':', scrap)
          
          if multiple_part is not None:
               #print sourcestring+' has multiple parts'
               #get all text under source if it has multiple parts
               multi_part_source=re.compile('<p>Source #'+sourcenumber+': (.+?)PART 1(.+?)</i><p>').findall(scrap)

               #put scrape back together
               for sourcescrape1,sourcescrape2 in multi_part_source:
                    scrape=sourcescrape1+'PART 1'+sourcescrape2

                    #check if source is megaupload or 2shared, and add all parts as links
                    ismega = re.search('.megaupload.com/', scrape)
                    is2shared = re.search('.2shared.com/', scrape)
                    if ismega is not None:
                         #print sourcestring+' is hosted by megaupload'
                         part=re.compile('&url=http://www.megaupload.com/?(.+?)>PART (.+?)</a>').findall(scrape)
                         for url,name in part:
                              #print 'scrapedmegaurl: '+url
                              fullurl='http://www.megaupload.com/'+url
                              #print 'megafullurl: '+fullurl
                              partname='Part '+name
                              fullname=sourcestring+' | MU | '+partname
                              Add_Multi_Parts(fullname,fullurl,megapic)
                    elif is2shared is not None and hide2shared == 'false':
                         #print sourcestring+' is hosted by 2shared' 
                         part=re.compile('&url=http://www.2shared.com/(.+?)>PART (.+?)</a>').findall(scrape)
                         for url,name in part:
                              #print 'scraped2shared: '+url
                              fullurl='http://www.2shared.com/'+url
                              #print '2sharedfullurl: '+fullurl
                              partname='Part '+name
                              fullname=sourcestring+' | 2S  | '+partname
                              Add_Multi_Parts(fullname,fullurl,shared2pic) 

          #if source does not have multiple parts...
          elif multiple_part is None:
               #print sourcestring+' is single part'
               #find corresponding '<a rel=?' entry and add as a one-link source
               source5=re.compile('<a rel='+sourcenumber+'.+?&url=(.+?)>Source #'+sourcenumber+':').findall(scrap)
               #print source5
               for url in source5:
                    ismega = re.search('.megaupload.com/', url)
                    is2shared = re.search('.2shared.com/', url)
                    if ismega is not None:
                         #print 'Source #'+sourcenumber+' is hosted by megaupload'
                         fullname=sourcestring+' | MU | Full'
                         addExecute(fullname,url,200,megapic)
                    elif is2shared is not None and hide2shared == 'false':
                         #print 'Source #'+sourcenumber+' is hosted by 2shared' 
                         fullname=sourcestring+' | 2S  | Full'
                         addExecute(fullname,url,200,shared2pic)


def SOURCE(scrape):
#check for sources containing multiple parts or just one part
          #get settings
          selfAddon = xbmcaddon.Addon(id='plugin.video.icefilms')
          
          hide2shared = selfAddon.getSetting('hide-2shared')
          megapic=handle_file('megapic','')
          shared2pic=handle_file('shared2pic','')

          #create a list of numbers 1-21
          num = 1
          numlist = list('1')
          while num < 21:
              num = num+1
              numlist.append(str(num))

          #for every number, run PART.
          #The first thing PART does is check whether that number source exists in the page source code...
          #...so it's not as CPU intensive as you might think.    
          for thenumber in numlist: 
               PART(scrape,thenumber,hide2shared,megapic,shared2pic)

           
def DVDRip(url):
        link=handle_file('mirror','open')
#string for all text under standard def border
        defcat=re.compile('<div class=ripdiv><b>DVDRip / Standard Def</b>(.+?)</div>').findall(link)
        for scrape in defcat:
                SOURCE(scrape)

def HD720p(url):
        link=handle_file('mirror','open')
#string for all text under hd720p border
        defcat=re.compile('<div class=ripdiv><b>HD 720p</b>(.+?)</div>').findall(link)
        for scrape in defcat:
                SOURCE(scrape)

def DVDScreener(url):
        link=handle_file('mirror','open')
#string for all text under dvd screener border
        defcat=re.compile('<div class=ripdiv><b>DVD Screener</b>(.+?)</div>').findall(link)
        for scrape in defcat:
                SOURCE(scrape)

def R5R6(url):
        link=handle_file('mirror','open')
#string for all text under r5/r6 border
        defcat=re.compile('<div class=ripdiv><b>R5/R6 DVDRip</b>(.+?)</div>').findall(link)
        for scrape in defcat:
                SOURCE(scrape)

class TwoSharedDownloader:
     
     def __init__(self):
          self.cookieString = ""
          self.re2sUrl = re.compile('(?<=window.location \=\')([^\']+)')
     
     def returnLink(self, pageUrl):

          # Open the 2Shared page and read its source to htmlSource
          request = urllib2.Request(pageUrl)
          response = urllib2.urlopen(request)
          htmlSource = response.read()
     
          # Search the source for link to the video and store it for later use
          match = self.re2sUrl.search(htmlSource)
          fileUrl = match.group(0)
          
          # Extract the cookies set by visiting the 2Shared page
          cookies = cookielib.CookieJar()
          cookies.extract_cookies(response, request)
          
          # Format the cookies so they can be used in XBMC
          for item in cookies._cookies['.2shared.com']['/']:
               self.cookieString += str(item) + "=" + str(cookies._cookies['.2shared.com']['/'][item].value) + "; "
               self.cookieString += "WWW_JSESSIONID=" + str(cookies._cookies['www.2shared.com']['/']['JSESSIONID'].value)

          # Arrange the spoofed header string in a format XBMC can read
          headers = urllib.quote("User-Agent=Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)|Accept=text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8|Accept-Language=en-us,en;q=0.5|Accept-Encoding=gzip,deflate|Accept-Charset=ISO-8859-1,utf-8;q=0.7,*;q=0.7|Keep-Alive=115|Referer=" + pageUrl + "|Cookie=" + self.cookieString)
          
          # Append the header string to the file URL
          pathToPlay = fileUrl + "?" + headers
          
          # Return the valid link
          return pathToPlay 
     

     
          
def SHARED2_HANDLER(url):
          downloader2Shared = TwoSharedDownloader()
          vidFile = downloader2Shared.returnLink(url)
          #vidFile = TwoSharedDownloader.returnLink(url)
          
          print str(vodFile)
          match=re.compile('http\:\/\/(.+?).dc1').findall(vidFile)
          for urlbulk in match:
               finalurl='http://'+urlbulk+'.avi'
               print '2Shared Direct Link: '+finalurl
               return finalurl
          #req = urllib2.Request(url)
          #req.add_header('User-Agent', USER_AGENT)
          #req.add_header('Referer', url)
          #jar = cookielib.FileCookieJar("cookies")
          #opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(jar))
          #response = opener.open(req)
          #link=response.read()
          #response.close()
          #dirlink=re.compile("window.location ='(.+?)';").findall(link)
          #for surl in dirlink:
          #    return surl

def GetURL(url, params = None, referrer = ICEFILMS_REFERRER):
     # print 'processing url: ' + url
     req = urllib2.Request(url)
     req.add_header('User-Agent', USER_AGENT)
     # as of 2011-06-02, IceFilms sources aren't displayed unless a valid referrer header is supplied:
     # http://forum.xbmc.org/showpost.php?p=810288&postcount=1146
     if referrer:
         req.add_header('Referer', referrer)
     # avoid Python >= 2.5 ternary operator for backwards compatibility
     # http://wiki.xbmc.org/index.php?title=Python_Development#Version
     if params:
        response = urllib2.urlopen(req, params)
     else:
        response = urllib2.urlopen(req)
     source = response.read()
     response.close()
     return source

def WaitIf():
     #killing playback is necessary if switching playing of one megaup/2share stream to another
     if xbmc.Player().isPlayingVideo() == True:
               #currentvid=xbmc.Player().getPlayingFile()
               #isice = re.search('.megaupload', currentvid)
                xbmc.Player().stop()

def cleanFilename(file, isPath=False):
    #Clean filename of not os allowed characters (replace with '_'
    file=file.replace(':','_').replace('<','_').replace('>','_').replace('*','_').replace('"','_').replace('|','_').replace('?','_')
    # if this isn't a path clean special path characters too
    if isPath == False:
        file=file.replace('/','_').replace('\\','_')
    print file
    
    return file

def Get_Path(srcname,vidname):
     ##Gets the path the file will be downloaded to, and if necessary makes the folders##
     
     #get settings
     selfAddon = xbmcaddon.Addon(id='plugin.video.icefilms')
          
     #get path for download
     mypath=os.path.normpath(str(selfAddon.getSetting('download-folder')))
     
     #clean video name of unwanted characters
     vidname = cleanFilename(vidname)
     if os.path.exists(mypath):

          #if source is split into parts, attach part number to the videoname.
          if re.search('Part',srcname) is not None:
               srcname=(re.split('\|+', srcname))[-1]
               vidname=vidname+' part'+((re.split('\ +', srcname))[-1])
               #add file extension
               vidname = vidname+'.avi'
          else:
               #add file extension
               vidname = vidname+'.avi'

          initial_path=os.path.join(mypath,'Icefilms Downloaded Videos')

          #is use special directory structure set to true?
          SpecialDirs=selfAddon.getSetting('use-special-structure')

          if SpecialDirs == 'true':
               mediapath=os.path.normpath(handle_file('mediapath','open'))
               mediapath = cleanFilename(mediapath, isPath=True)
               mediapath=os.path.join(initial_path,mediapath)              
               
               if not os.path.exists(mediapath):
                    os.makedirs(mediapath)
               finalpath=os.path.join(mediapath,vidname)
               return finalpath
     
          elif SpecialDirs == 'false':
               mypath=os.path.join(initial_path,vidname)
               return mypath
     else:
          return 'path not set'


def Item_Meta(name):
          #set metadata, for selected source. this is done from 'phantom meta'.
          # ie, meta saved earlier when we loaded the mirror page.
          # very important that things are contained within try blocks, because streaming will fail if something in this function fails.

          #set name and description, unicode cleaned.
          try: open_vidname=handle_file('videoname','open')
          except:
               vidname = ''
               print 'OPENING VIDNAME FAILED!'
          else:
               try: get_vidname = htmlcleaner.clean(open_vidname)
               except:
                    print 'CLEANING VIDNAME FAILED! :',open_vidname
                    vidname = open_vidname
               else: vidname = get_vidname

          try: open_desc=handle_file('description','open')
          except:
               description = ''
               print 'OPENING DESCRIPTION FAILED!'
          else:
               try: get_desc = htmlcleaner.clean(open_desc)
               except:
                    print 'CLEANING DESCRIPTION FAILED! :',open_desc
                    description = open_desc
               else: description = get_desc
          
          #set other metadata strings from strings saved earlier
          try: get_poster=handle_file('poster','open')
          except: poster = ''
          else: poster = get_poster

          try: get_mpaa=handle_file('mpaa','open')
          except: mpaa = None
          else: mpaa = get_mpaa
          
          #srcname=handle_file('sourcename','open')
          srcname=name

          listitem = xbmcgui.ListItem(srcname)
          if not mpaa:
               listitem.setInfo('video', {'Title': vidname, 'plotoutline': description, 'plot': description})
          if mpaa:
               listitem.setInfo('video', {'Title': vidname, 'plotoutline': description, 'plot': description, 'mpaa': mpaa})
          listitem.setThumbnailImage(poster)

          return listitem


def do_wait(account):
     # do the necessary wait, with  a nice notice and pre-set waiting time. I have found the below waiting times to never fail.
     
     if account == 'premium':
          return handle_wait(5,'Megaupload','Loading video with your *Premium* account.')

     elif account == 'free':
          return handle_wait(26,'Megaupload Free User','Loading video with your free account.')

     elif account == 'none':
          return handle_wait(46,'Megaupload','Loading video.')
    


def handle_wait(time_to_wait,title,text):

    print 'waiting '+str(time_to_wait)+' secs'    

    pDialog = xbmcgui.DialogProgress()
    ret = pDialog.create(' '+title)

    secs=0
    percent=0
    increment = int(100 / time_to_wait)

    cancelled = False
    while secs < time_to_wait:
        secs = secs + 1
        percent = increment*secs
        secs_left = str((time_to_wait - secs))
        remaining_display = ' Wait '+secs_left+' seconds for the video stream to activate...'
        pDialog.update(percent,' '+text,remaining_display)
        xbmc.sleep(1000)
        if (pDialog.iscanceled()):
             cancelled = True
             break
    if cancelled == True:     
         print 'wait cancelled'
         return False
    else:
         print 'done waiting'
         return True

def Handle_Vidlink(url):
     #video link preflight, pays attention to settings / checks if url is mega or 2shared
     ismega = re.search('.megaupload.com/', url)
     is2shared = re.search('.2shared.com/', url)
     
     if ismega is not None:
          WaitIf()
          
          mu = megaroutines.megaupload(translatedicedatapath)
          link = mu.resolve_megaup(url)

          finished = do_wait(link[3])

          if finished == True:
               return link
          else:
               return None

     elif is2shared is not None:
          return False
          Notify('big','2Shared','2Shared is not supported by this addon. (Yet)','')
          #shared2url=SHARED2_HANDLER(url)
          #return shared2url

def PlayFile(name,url):
    
    listitem=Item_Meta(name)
    print 'attempting to play local file'
    try:
        #directly call xbmc player (provides more options)
        xbmc.Player( xbmc.PLAYER_CORE_DVDPLAYER ).play( url, listitem )
    except:
        print 'local file playing failed'

def Stream_Source(name,url):
     link=Handle_Vidlink(url)
     listitem=Item_Meta(name)
     print 'attempting to stream file'
     try:
          #directly call xbmc player (provides more options)
          xbmc.Player( xbmc.PLAYER_CORE_DVDPLAYER ).play( link[0], listitem )
     except:
          print 'file streaming failed'
          Notify('megaalert','','','')



def Download_Source(name,url):

    #get proper name of vid
    vidname=handle_file('videoname','open')
    
    mypath=Get_Path(name,vidname)
    
    #get settings
    selfAddon = xbmcaddon.Addon(id='plugin.video.icefilms')
       
    print 'MYPATH: ',mypath
    if mypath == 'path not set':
        Notify('Download Alert','You have not set the download folder.\n Please access the addon settings and set it.','','')
    
    else:
        if os.path.isfile(mypath) is True:
            Notify('Download Alert','The video you are trying to download already exists!','','')
        else:              
            link=Handle_Vidlink(url)
            DownloadInBack=selfAddon.getSetting('download-in-background')
            print 'attempting to download file, silent = '+ DownloadInBack
            try:
                if DownloadInBack == 'true':
                    QuietDownload(link[0], mypath, vidname)
                else:
                    Download(link[0], mypath, vidname)
            except:
                print 'download failed'

def Check_Mega_Limits(name,url):
     WaitIf()
     mu=megaroutines.megaupload(translatedicedatapath)
     limit=mu.dls_limited()
     if limit is True:
          Notify('megaalert1','','','')
     elif limit is False:
          Notify('megaalert2','','','')

def Kill_Streaming(name,url):
     xbmc.Player().stop()     

class StopDownloading(Exception): 
        def __init__(self, value): 
            self.value = value 
        def __str__(self): 
            return repr(self.value)
          
def Download(url, dest, displayname=False):
        #get settings
        selfAddon = xbmcaddon.Addon(id='plugin.video.icefilms')
          
        if displayname == False:
            displayname=url
        DeleteIncomplete=selfAddon.getSetting('delete-incomplete-downloads')
        dp = xbmcgui.DialogProgress()
        dp.create('Downloading', '', displayname)
        start_time = time.time() 
        try: 
            urllib.urlretrieve(url, dest, lambda nb, bs, fs: _pbhook(nb, bs, fs, dp, start_time)) 
        except:
            if DeleteIncomplete == 'true':
                #delete partially downloaded file if setting says to.
                while os.path.exists(dest): 
                    try: 
                        os.remove(dest) 
                        break 
                    except: 
                        pass 
            #only handle StopDownloading (from cancel), ContentTooShort (from urlretrieve), and OS (from the race condition); let other exceptions bubble 
            if sys.exc_info()[0] in (urllib.ContentTooShortError, StopDownloading, OSError): 
                return 'false' 
            else: 
                raise 
        return 'downloaded'

'''     
def QuietDownload(url, dest):
#possibly useful in future addon versions
     
        #dp = xbmcgui.DialogProgress() 
        #dp.create('Downloading', '', name) 
        start_time = time.time() 
        try: 
            #urllib.urlretrieve(url, dest, lambda nb, bs, fs: _pbhook(nb, bs, fs, dp, start_time))
            urllib.urlretrieve(url, dest)
            #xbmc.Player().play(dest)
        except: 
            #delete partially downloaded file 
            while os.path.exists(dest): 
                try: 
                    #os.remove(dest) 
                    break 
                except: 
                     pass 
            #only handle StopDownloading (from cancel), ContentTooShort (from urlretrieve), and OS (from the race condition); let other exceptions bubble 
            if sys.exc_info()[0] in (urllib.ContentTooShortError, StopDownloading, OSError): 
                return 'false' 
            else: 
                raise 
        return 'downloaded' 
'''
def QuietDownload(url, dest, videoname):
    #quote parameters passed to download script     
    q_url = urllib.quote_plus(url)
    q_dest = urllib.quote_plus(dest)
    q_vidname = urllib.quote_plus(videoname)
    
    #Create possible values for notification
    notifyValues = [2, 5, 10, 20, 25, 50, 100]
    #get settings
    selfAddon = xbmcaddon.Addon(id='plugin.video.icefilms')
    # get notify value from settings
    NotifyPercent=int(selfAddon.getSetting('notify-percent'))
    
    script = os.path.join( icepath, 'resources', 'lib', "DownloadInBackground.py" )
    xbmc.executebuiltin( "RunScript(%s, %s, %s, %s, %s)" % ( script, q_url, q_dest, q_vidname, str(notifyValues[NotifyPercent]) ) )
             

def _pbhook(numblocks, blocksize, filesize, dp, start_time):
        try: 
            percent = min(numblocks * blocksize * 100 / filesize, 100) 
            currently_downloaded = float(numblocks) * blocksize / (1024 * 1024) 
            kbps_speed = numblocks * blocksize / (time.time() - start_time) 
            if kbps_speed > 0: 
                eta = (filesize - numblocks * blocksize) / kbps_speed 
            else: 
                eta = 0 
            kbps_speed = kbps_speed / 1024 
            total = float(filesize) / (1024 * 1024) 
            # print ( 
                # percent, 
                # numblocks, 
                # blocksize, 
                # filesize, 
                # currently_downloaded, 
                # kbps_speed, 
                # eta, 
                # ) 
            mbs = '%.02f MB of %.02f MB' % (currently_downloaded, total) 
            e = 'Speed: %.02f Kb/s ' % kbps_speed 
            e += 'ETA: %02d:%02d' % divmod(eta, 60) 
            dp.update(percent, mbs, e)
            #print percent, mbs, e 
        except: 
            percent = 100 
            dp.update(percent) 
        if dp.iscanceled(): 
            dp.close() 
            raise StopDownloading('Stopped Downloading')

   
def addExecute(name,url,mode,iconimage):

    # A list item that executes the next mode, but doesn't clear the screen of current list items.

    #encode url and name, so they can pass through the sys.argv[0] related strings
    sysname = urllib.quote_plus(name)
    sysurl = urllib.quote_plus(url)
    
    u = sys.argv[0] + "?url=" + sysurl + "&mode=" + str(mode) + "&name=" + sysname
    ok=True

    liz=xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=iconimage)
    liz.setInfo( type="Video", infoLabels={ "Title": name } )

    #handle adding context menus
    contextMenuItems = []

    contextMenuItems.append(('Download', 'XBMC.RunPlugin(%s?mode=201&name=%s&url=%s)' % (sys.argv[0], sysname, sysurl)))
    contextMenuItems.append(('Download with jDownloader', 'XBMC.RunPlugin(plugin://plugin.program.jdownloader/?action=addlink&url=%s)' % (sysurl)))
    contextMenuItems.append(('Check Mega Limits', 'XBMC.RunPlugin(%s?mode=202&name=%s&url=%s)' % (sys.argv[0], sysname, sysurl)))
    contextMenuItems.append(('Kill Streams', 'XBMC.RunPlugin(%s?mode=203&name=%s&url=%s)' % (sys.argv[0], sysname, sysurl)))

    liz.addContextMenuItems(contextMenuItems, replaceItems=True)

    ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=False)
    return ok


def addDir(name, url, mode, iconimage, metainfo=False, imdb=False, delfromfav=False, total=False, disablefav=False, searchMode=False):
    if xbmc_imported:
         meta = metainfo
         
         ###  addDir with context menus and meta support  ###

         #encode url and name, so they can pass through the sys.argv[0] related strings
         sysname = urllib.quote_plus(name)
         sysurl = urllib.quote_plus(url)
         dirmode=mode
         
         #get nice unicode name text.
         #name has to pass through lots of weird operations earlier in the script,
         #so it should only be unicodified just before it is displayed.
         name = htmlcleaner.clean(name)
         
         if mode == 12 or mode == 13:
             u = sys.argv[0] + "?url=" + sysurl + "&mode=" + str(mode) + "&name=" + sysname + "&imdbnum=" + urllib.quote_plus(str(imdb))
         else:
             u = sys.argv[0] + "?url=" + sysurl + "&mode=" + str(mode) + "&name=" + sysname
         ok = True
         
         if meta is not False:
             print str(meta)
         #handle adding context menus
         contextMenuItems = []
         
         #handle adding meta
         if meta == False:
             liz = xbmcgui.ListItem(name, iconImage=iconimage, thumbnailImage=iconimage)
             liz.setInfo(type="Video", infoLabels={"Title": name})

         else:
             
             if meta.has_key('watched') == False :
                 meta['watched']=6 
             liz = xbmcgui.ListItem(name, iconImage=str(meta['cover_url']), thumbnailImage=str(meta['cover_url']))
             
             infoLabels = {}
             infoLabels['title'] = name
             infoLabels['plot'] = cleanUnicode(meta['plot']) # to-check if we need cleanUnicode
             infoLabels['genre'] = str(meta['genres'])
             infoLabels['duration'] = str(meta['duration'])
             infoLabels['premiered'] = str(meta['premiered'])
             infoLabels['studio'] = meta['studios']
             infoLabels['mpaa'] = str(meta['mpaa'])
             infoLabels['code'] = str(meta['imdb_id'])
             infoLabels['rating'] = float(meta['rating'])
             infoLabels['overlay'] = meta['watched'] # watched 7, unwatched 6
             
             try:
                     trailer_id = re.match('^[^v]+v=(.{11}).*', meta['trailer_url']).group(1)
                     infoLabels['trailer'] = "plugin://plugin.video.youtube/?action=play_video&videoid=%s" % trailer_id
             except:
                     infoLabels['trailer'] = ''
             
             if meta.has_key('season_num'):
                 infoLabels['Episode'] = int(meta['episode_num'])
                 infoLabels['Season'] =int(meta['season_num'])
                 print 'No refresh for episodes yet'
             elif searchMode==False:
                 #print 'Mode is ' + str(mode) + ' argv is ' + str(sys.argv[1]) + ' name is ' + sysname
                 contextMenuItems.append(('Refresh Info', 'XBMC.RunPlugin(%s?mode=999&name=%s&url=%s&imdbnum=%s&dirmode=%s)' % (sys.argv[0], sysname, sysurl, urllib.quote_plus(str(imdb)), dirmode)))
                 contextMenuItems.append(('Search for trailer', 
                                          'XBMC.RunPlugin(%s?mode=998&name=%s&url=%s&dirmode=%s&imdbnum=%s)' 
                                          % (sys.argv[0], sysname, sysurl, dirmode, urllib.quote_plus(str(imdb))) ))
                 #if str(meta['trailer_url']) != 'None' and str(meta['trailer_url']) != '':
                     #print 'Trailer link -------  ' + 'plugin://plugin.video.youtube/?action=play_video&videoid=%s' % str(meta['trailer_url'])[str(meta['trailer_url']).rfind("v=")+2:] #str(meta['trailer_url'])
                     #contextMenuItems.append(('Play Trailer', 'XBMC.PlayMedia(plugin://plugin.video.youtube/?action=play_video&videoid=%s)' % str(meta['trailer_url'])[str(meta['trailer_url']).rfind("v=")+2:]))
             
             # mark as watched or unwatched 
             addWatched = False
             videoType = ''
             season=''
             if mode == 12: # TV series
                 addWatched = True
                 videoType = 'tvshow'
                 if searchMode == False:
                     contextMenuItems.append(('Show Information', 'XBMC.Action(Info)'))
             elif meta.has_key('season_num'): # episode
                 addWatched = True
                 videoType = 'episode'
                 season = meta['season']
                 if searchMode == False:
                     contextMenuItems.append(('Episode Information', 'XBMC.Action(Info)'))
             elif mode == 100: # movies
                 addWatched = True
                 videoType = 'movie'
                 if searchMode == False:
                     contextMenuItems.append(('Movie Information', 'XBMC.Action(Info)'))
             if addWatched:
                 if meta['watched'] == 6:
                     watchedMenu='Mark as Watched'
                 else:
                     watchedMenu='Mark as Unwatched'
                 if searchMode==False:
                     contextMenuItems.append((watchedMenu, 'XBMC.RunPlugin(%s?mode=990&name=%s&url=%s&imdbnum=%s&videoType=%s&season=%s)' 
                         % (sys.argv[0], sysname, sysurl, urllib.quote_plus(str(imdb)), videoType, urllib.quote_plus(season))))
             
             liz.setInfo(type="Video", infoLabels=infoLabels)
         
         # add/delete favourite
         if disablefav is False: # disable fav is necessary for the scrapes in the homepage category.
             if delfromfav is True:
                 #settings for when in the Favourites folder
                 contextMenuItems.append(('Delete from Ice Favourites', 'XBMC.RunPlugin(%s?mode=111&name=%s&url=%s)' % (sys.argv[0], sysname, sysurl)))
             else:
                 #if directory is an episode list or movie
                 if mode == 100 or mode == 12:
                     if imdb is not False:
                         sysimdb = urllib.quote_plus(str(imdb))
                     else:
                         #if no imdb number, it will have no metadata in Favourites
                         sysimdb = urllib.quote_plus('nothing')
                     if searchMode==False:
                         contextMenuItems.append(('Add to Ice Favourites', 'XBMC.RunPlugin(%s?mode=110&name=%s&url=%s&imdbnum=%s)' % (sys.argv[0], sysname, sysurl, sysimdb)))

         # switch on/off library mode (have it appear in list after favourite options)
         if inLibraryMode():
             contextMenuItems.append(('Switch off Library mode', 'XBMC.RunPlugin(%s?mode=300)' % (sys.argv[0])))
         else:
             contextMenuItems.append(('Switch to Library Mode', 'XBMC.RunPlugin(%s?mode=300)' % (sys.argv[0])))
             
         if contextMenuItems:
             #print str(contextMenuItems)
             liz.addContextMenuItems(contextMenuItems, replaceItems=True)
         #########

         print '          Mode=' + str(mode) + ' URL=' + str(url)
         #Do some crucial stuff
         if total is False:
             ok = xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u, listitem=liz, isFolder=True)
         else:
             ok = xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u, listitem=liz, isFolder=True, totalItems=int(total))
         return ok
     

#VANILLA ADDDIR (kept for reference)
def VaddDir(name,url,mode,iconimage):
        u=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)
        ok=True
        liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
        liz.setInfo( type="Video", infoLabels={ "Title": name } )
        ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
        return ok

# switch in and out of library mode
def toggleLibraryMode():
    container_folder_path = xbmc.getInfoLabel('Container.FolderPath')
    if inLibraryMode():
        xbmc.executebuiltin("XBMC.ActivateWindow(VideoFiles,%s)" % container_folder_path)
        # do not cacheToDisc cuz we want this code rerun
        xbmcplugin.endOfDirectory( int(sys.argv[1]), succeeded=True, updateListing=False, cacheToDisc=False )
    else:
        xbmc.executebuiltin("XBMC.ActivateWindow(VideoLibrary,%s)" % container_folder_path)
        # do not cacheToDisc cuz we want this code rerun
        xbmcplugin.endOfDirectory( int(sys.argv[1]), succeeded=True, updateListing=False, cacheToDisc=False )

def inLibraryMode():
    return xbmc.getCondVisibility("[Window.IsActive(videolibrary)]")

def setView(content, viewType):
    #get settings
    selfAddon = xbmcaddon.Addon(id='plugin.video.icefilms')
    
    # kept for reference only
    #movies_view = selfAddon.getSetting('movies-view')
    #tvshows_view = selfAddon.getSetting('tvshows-view')
    #episodes_view = selfAddon.getSetting('episodes-view')
    #
    
    # set content type so library shows more views and info
    xbmcplugin.setContent(int(sys.argv[1]), content)
    if selfAddon.getSetting('auto-view') == 'true':
        xbmc.executebuiltin("Container.SetViewMode(%s)" % selfAddon.getSetting(viewType) )
    
    # set sort methods - probably we don't need all of them
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_UNSORTED )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_LABEL )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_VIDEO_RATING )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_DATE )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_PROGRAM_COUNT )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_VIDEO_RUNTIME )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_GENRE )
    
#Movie Favourites folder.
def MOVIE_FAVOURITES(url):
    
    #get settings
    selfAddon = xbmcaddon.Addon(id='plugin.video.icefilms')
    favpath=os.path.join(translatedicedatapath,'Favourites')
    moviefav=os.path.join(favpath,'Movies')
    try:
        moviedircontents=os.listdir(moviefav)
    except:
        moviedircontents=None
    
    if moviedircontents == None:
        Notify('big','No Movie Favourites Saved','To save a favourite press the C key on a movie or\n TV Show and select Add To Icefilms Favourites','')
    
    else:
        #add clear favourites entry - Not sure if we must put it here, cause it will mess up the sorting
        #addExecute('* Clear Favourites Folder *',url,58,os.path.join(art,'deletefavs.png'))
        
        #handler for all movie favourites
        if moviedircontents is not None:
            
            #get the necessary meta stuff
            use_meta=os.path.exists(os.path.join(translatedicedatapath,'meta_caches'))
            meta_setting = selfAddon.getSetting('use-meta')
            
            #add without metadata -- imdb is still passed for use with Add to Favourites
            if use_meta==False or meta_setting=='false':
                addFavourites(False,moviefav,moviedircontents, 'movie')
            
            #add with metadata -- imdb is still passed for use with Add to Favourites
            elif use_meta==True and meta_setting=='true':
                addFavourites(True,moviefav,moviedircontents, 'movie')
        else:
            print 'moviedircontents is none!'
            
    # Enable library mode & set the right view for the content
    setView('movies', 'movies-view')

#TV Shows Favourites folder
def TV_FAVOURITES(url):
    
    #get settings
    selfAddon = xbmcaddon.Addon(id='plugin.video.icefilms')
    favpath=os.path.join(translatedicedatapath,'Favourites')
    tvfav=os.path.join(favpath,'TV')
    try:
        tvdircontents=os.listdir(tvfav)
    except:
        tvdircontents=None
 
    if tvdircontents == None:
        Notify('big','No TV Favourites Saved','To save a favourite press the C key on a movie or\n TV Show and select Add To Icefilms Favourites','')

    else:
        #add clear favourites entry - Not sure if we must put it here, cause it will mess up the sorting
        #addExecute('* Clear Favourites Folder *',url,58,os.path.join(art,'deletefavs.png'))
               
        #handler for all tv favourites
        if tvdircontents is not None:
            
            #get the necessary meta stuff
            use_meta=os.path.exists(os.path.join(translatedicedatapath,'meta_caches'))
            meta_setting = selfAddon.getSetting('use-meta')
            
            #add without metadata -- imdb is still passed for use with Add to Favourites
            if use_meta==False or meta_setting=='false':
                addFavourites(False,tvfav,tvdircontents,'tvshow')
                
            #add with metadata -- imdb is still passed for use with Add to Favourites
            elif use_meta==True and meta_setting=='true':
                addFavourites(True,tvfav,tvdircontents,'tvshow')             
        else:
            print 'tvshows dircontents is none!'
    
    # Enable library mode & set the right view for the content
    setView('movies', 'tvshows-view')


def cleanUnicode(string):
    try:
        string = string.replace("'","").replace(unicode(u'\u201c'), '"').replace(unicode(u'\u201d'), '"').replace(unicode(u'\u2019'),'').replace(unicode(u'\u2026'),'...').replace(unicode(u'\u2018'),'').replace(unicode(u'\u2013'),'-')
        return string
    except:
        return string

def getMeta(scrape, mode):
    #get settings
    selfAddon = xbmcaddon.Addon(id='plugin.video.icefilms')
    meta_path=os.path.join(translatedicedatapath,'meta_caches')
    use_meta=os.path.exists(meta_path)
    meta_setting = selfAddon.getSetting('use-meta')
    #check settings over whether to display the number of episodes next to tv show name.
    show_num_of_eps=selfAddon.getSetting('display-show-eps')
    
    #print scrape

    #add without metadata -- imdb is still passed for use with Add to Favourites
    if use_meta==False or meta_setting=='false':
        for imdb_id,url,name in scrape:
            name=CLEANUP(name)
            addDir(name,iceurl+url,mode,'',imdb='tt'+str(imdb_id))
            
    #add with metadata
    elif use_meta==True and meta_setting=='true':
    
        #initialise meta class before loop
        metaget=metahandlers.MetaData(metapath,preparezip = xbmc_imported)

        #determine whether to show number of eps
        if scrape[3] and show_num_of_eps == 'true' and mode == 12:
            for imdb_id,url,name,num_of_eps in scrape:
                num_of_eps=re.sub('<','',num_of_eps)
                num_of_eps=re.sub('isode','',num_of_eps)#turn Episode{s} into Ep(s)
                ADD_ITEM(metaget,imdb_id,url,name,mode,num_of_eps)
        elif mode == 12: # fix for tvshows with num of episodes disabled
            for imdb_id,url,name,num_of_eps in scrape:
                ADD_ITEM(metaget,imdb_id,url,name,mode)
        else:
            for imdb_id,url,name in scrape:
                ADD_ITEM(metaget,imdb_id,url,name,mode)

def ADD_ITEM(metaget,imdb_id,url,name,mode,num_of_eps=False):
            #clean name of unwanted stuff
            name=CLEANUP(name)
            if url.startswith('http://www.icefilms.info') == False:
                url=iceurl+url
            meta = {}

            #return the metadata dictionary
            if mode==100:
                #return the metadata dictionary
                meta=metaget.get_meta(imdb_id, 'movie', CLEANUP_FOR_META(name), url)
            elif mode==12:
                #return the metadata dictionary
                meta=metaget.get_meta(imdb_id, 'tvshow', CLEANUP_FOR_META(name), url)

            #append number of episodes to the display name, AFTER THE NAME HAS BEEN USED FOR META LOOKUP
            if num_of_eps is not False:
                name = name + ' ' + str(num_of_eps)
                 
            #debugs
            print 'meta_name:'+str(name)
            #print 'meta_imdb_id:'+str(imdb_id)
            #print 'meta_video_url:'+str(url)
            #print 'meta_data:'+str(meta)
            #print 'meta_imdb_id:',meta['imdb_id']

            if meta is None:
                #add directories without meta
                if imdb_id == None:
                	imdb_id == ''
                else:
                	imdb_id = 'tt'+str(imdb_id)
                addDir(name,url,mode,'',imdb=imdb_id)
            else:
                #add directories with meta
                addDir(name,url,mode,'',metainfo=meta,imdb='tt'+str(imdb_id))

        
def REFRESH(url,imdb_id,name,dirmode):
        #refresh info for a Tvshow or movie
        
        #get settings
        selfAddon = xbmcaddon.Addon(id='plugin.video.icefilms')
        
        print 'In Refresh ' + str(sys.argv[1])
        imdb_id = imdb_id.replace('tttt','')
        meta_path=os.path.join(translatedicedatapath,'meta_caches')
        use_meta=os.path.exists(meta_path)
        meta_setting = selfAddon.getSetting('use-meta')

        if use_meta==False or meta_setting=='false':
            print 'do not use meta ' 
            for imdb_id,url,name in scrape:
                name=CLEANUP(name)
                addDir(name,iceurl+url,dirmode,'',imdb='tt'+str(imdb_id))   
        #add with metadata
        elif use_meta==True and meta_setting=='true':
             
            #initialise meta class before loop
            metaget=metahandlers.MetaData(translatedicedatapath)
            
            #for imdb_id,url,name in scrape:
                
            #clean name of unwanted stuff
            name=CLEANUP(name)
            if url.startswith('http://www.icefilms.info') == False:
                url=iceurl+url
            print 'IMDB before refresh is ' + imdb_id   
            #return the metadata dictionary  
            meta = {}
            if dirmode==100:
                # get ice_id from url
                ice_id=str(url).replace('http://www.icefilms.info/ip.php?v=','')
                if len(ice_id) > 0:
                    if ice_id.endswith('&') is False:
                        ice_id = ice_id + '&'
                    print ice_id
                else:
                    ice_id = ''
                    print 'Could not find the url ice_id for video ' + name
                #return the metadata dictionary
                meta=metaget.get_meta(imdb_id, 'movie', name, ice_id, refresh=True)
            elif dirmode==12:
                # get ice_id from url
                ice_id=str(url).replace('http://www.icefilms.info/tv/series/','')
                if len(ice_id) == 0 or ice_id is None:
                    ice_id = ''
                    print 'Could not find the url ice_id for tv show ' + name
                #return the metadata dictionary
                meta=metaget.get_meta(imdb_id, 'tvshow',name, ice_id, refresh=True)
               
            #debugs
            print 'meta_name:'+str(name)
            print 'meta_imdb_id:'+str(imdb_id)
            print 'meta_video_url:'+str(url)
            print 'meta_data:'+str(meta)
            print 'meta_imdb_id:',meta['imdb_id']
            #name = 'test'
            if meta is None:
                #add directories without meta
                addDir(name,url,dirmode,'')
            else:
                #add directories with meta
                addDir(name,url,int(dirmode),'',metainfo=meta,imdb=''+str(imdb_id))
            xbmc.executebuiltin("XBMC.Container.Refresh")

                
def get_episode(season, episode, imdb_id, url):
        #get settings
        selfAddon = xbmcaddon.Addon(id='plugin.video.icefilms')

        # displays all episodes in the source it is passed.
        meta_path=os.path.join(translatedicedatapath,'meta_caches')
        use_meta=os.path.exists(meta_path)
        meta_setting = selfAddon.getSetting('use-meta')
        imdb_id = imdb_id.replace('t','')
        #add without metadata -- imdb is still passed for use with Add to Favourites
        if use_meta==False or meta_setting=='false':
            episode=CLEANUP(episode)
            addDir(episode,iceurl+url,100,'',imdb='tt'+str(imdb_id))
                
        #add with metadata
        elif use_meta==True and meta_setting=='true':
            #initialise meta class before loop
            metaget=metahandlers.MetaData(translatedicedatapath) 
            
            #clean name of unwanted stuff
            episode=CLEANUP(episode)
            if url.startswith('http://www.icefilms.info') == False:
                url=iceurl+url
            meta = {}
            
            # get ice_id from url
            ice_id=str(url).replace('http://www.icefilms.info/ip.php?v=','')
            if len(ice_id) > 0:
                if ice_id.endswith('&') is False:
                    ice_id = ice_id + '&'
                print ice_id
            else:
                ice_id = ''
                print 'Could not find the url ice_id for episode ' + episode
                
            #return the metadata dictionary
            meta=metaget.get_episode_meta(imdb_id, season, episode, ice_id)
            
            #debugs
            print 'meta_name:'+str(name)
            #print 'meta_imdb_id:'+str(imdb_id)
            #print 'meta_video_url:'+str(url)
            print 'meta_data:'+str(meta)
            #print 'meta_imdb_id:',meta['imdb_id']
           
            if meta is None:
                #add directories without meta
                addDir(episode,iceurl+url,100,'')
            else:
                #add directories with meta
                addDir(episode,url,100,'',metainfo=meta,imdb='tt'+str(imdb_id))

               
def find_meta_for_search_results(results, mode, search=''):
    if mode == 100:
        #initialise meta class before loop
        metaget=metahandlers.MetaData(translatedicedatapath)
        for res in results:
            name=res.title.encode('utf8')
            name=CLEANSEARCH(name)
            url=res.url.encode('utf8')
            url=re.sub('&amp;','&',url)
            if url.startswith('http://www.icefilms.info/ip'):
                ice_id=str(url).replace('http://www.icefilms.info/ip.php?v=','')
                if len(ice_id) > 0:
                    if ice_id.endswith('&') is False:
                        ice_id = ice_id + '&'
                    print ice_id
                else:
                    ice_id = ''
                    print 'Could not find the url ice_id for video ' + str(url)
                    
                #return the metadata dictionary    
                meta=metaget._cache_lookup_by_url(ice_id)
                if meta is None:
                    addDir(name,url,100,'',searchMode=True)
                else:
                    #add directories with meta
                    addDir(name,url,mode,'',metainfo=meta,imdb=meta['imdb_id'],searchMode=True)
            else:
                addDir(name,url,100,'',searchMode=True)
    elif mode == 12:
        #initialise meta class before loop
        metaget=metahandlers.MetaData(translatedicedatapath)
        for myurl,interim,name in results:
            if len(interim) < 80:
                name=CLEANSEARCH(name)                              
                hasnameintitle=re.search(search,name,re.IGNORECASE)
                if hasnameintitle is not None:
                    myurl='http://www.icefilms.info/tv/series'+myurl
                    myurl=re.sub('&amp;','',myurl)
                    if myurl.startswith('http://www.icefilms.info/tv/series'):
                        ice_id=str(myurl).replace('http://www.icefilms.info/tv/series/','').replace('.html', '')
                        print ice_id
                        
                        #return the metadata dictionary
                        meta=metaget._cache_lookup_by_url(ice_id)
                        if meta is None:
                            addDir(name,myurl,12,'',searchMode=True)
                        else:
                            print meta
                            #add directories with meta
                            addDir(name,myurl,12,'',metainfo=meta,imdb=meta['imdb_id'],searchMode=True)
                    else:
                        addDir(name,myurl,12,'',searchMode=True)
 
         
def SearchGoogle(search):
    gs = GoogleSearch(''+search+' site:http://www.youtube.com ')
    gs.results_per_page = 25
    gs.page = 0
    results = gs.get_results()
    
    return results
                               
def SearchForTrailer(search, imdb_id, type, manual=False):
    search = search.replace(' *HD 720p*', '')
    res_name = []
    res_url = []
    res_name.append('Nothing Found. Thanks!!!')
    res_name.append('Manualy enter search...')
    
    if manual:
        results = SearchGoogle(search)
        for res in results:
            if res.url.encode('utf8').startswith('http://www.youtube.com/watch'):
                res_name.append(res.title.encode('utf8'))
                res_url.append(res.url.encode('utf8'))
    else:
        results = SearchGoogle(search+' official trailer')
        for res in results:
            if res.url.encode('utf8').startswith('http://www.youtube.com/watch'):
                res_name.append(res.title.encode('utf8'))
                res_url.append(res.url.encode('utf8'))
        results = SearchGoogle(search[:(len(search)-7)]+' official trailer')
        for res in results:
            if res.url.encode('utf8').startswith('http://www.youtube.com/watch') and res.url.encode('utf8') not in res_url:
                res_name.append(res.title.encode('utf8'))
                res_url.append(res.url.encode('utf8'))
            
    dialog = xbmcgui.Dialog()
    ret = dialog.select(search + ' trailer search',res_name)
    
    # Manual search for trailer
    if ret == 1:
        if manual:
            default = search
            title = 'Manual Search for '+search
        else:
            default = search+' official trailer'
            title = 'Manual Trailer Search for '+search
        keyboard = xbmc.Keyboard(default, title)
        #keyboard.setHiddenInput(hidden)
        keyboard.doModal()
        
        if keyboard.isConfirmed():
            result = keyboard.getText()
            SearchForTrailer(result, imdb_id, type, manual=True) 
    # Found trailers
    elif ret > 1:
        trailer_url = res_url[ret - 2]
        print trailer_url
        xbmc.executebuiltin(
            "PlayMedia(plugin://plugin.video.youtube/?action=play_video&videoid=%s&quality=720p)" 
            % str(trailer_url)[str(trailer_url).rfind("v=")+2:] )
        
        #dialog.ok(' title ', ' message ')
        metaget=metahandlers.MetaData(translatedicedatapath)
        if type==100:
            type='movie'
        elif type==12:
            type='tvshow'
        metaget.update_trailer(imdb_id, type, trailer_url)
        xbmc.executebuiltin("XBMC.Container.Refresh")

def ChangeWatched(imdb_id, videoType, name, season):
    metaget=metahandlers.MetaData(translatedicedatapath)
    metaget.change_watched(imdb_id, videoType, name, season)
    xbmc.executebuiltin("XBMC.Container.Refresh")

def get_params():
        param=[]
        paramstring=sys.argv[2]
        if len(paramstring)>=2:
                params=sys.argv[2]
                cleanedparams=params.replace('?','')
                if (params[len(params)-1]=='/'):
                        params=params[0:len(params)-2]
                pairsofparams=cleanedparams.split('&')
                param={}
                for i in range(len(pairsofparams)):
                        splitparams={}
                        splitparams=pairsofparams[i].split('=')
                        if (len(splitparams))==2:
                                param[splitparams[0]]=splitparams[1]
                                
        return param

params=get_params()
url=None
name=None
mode=None
imdbnum=None
dirmode=None
season=None
type=None

try:
        url=urllib.unquote_plus(params["url"])
except:
        pass
try:
        name=urllib.unquote_plus(params["name"])
except:
        pass
try:
        imdbnum=urllib.unquote_plus(params["imdbnum"])
except:
        pass
try:
        mode=int(params["mode"])
except:
        pass
try:
        dirmode=int(params["dirmode"])
except:
        pass
try:
        season=urllib.unquote_plus(params["season"])
        #season=params["season"]
except:
        pass
try:
        type=urllib.unquote_plus(params["videoType"])
except:
        pass

print '==========================PARAMS:\nURL: %s\nNAME: %s\nMODE: %s\nIMDBNUM: %s\nMYHANDLE: %s\nPARAMS: %s' % ( url, name, mode, imdbnum, sys.argv[1], params )

if mode==None: #or url==None or len(url)<1:
        print ""
        CATEGORIES()

elif mode==999:
        print "Mode 999 ******* dirmode is " + str(dirmode) + " *************  url is -> "+url
        REFRESH(url,imdbnum,name,dirmode)

elif mode==998:
        print "Mode 998 (trailer search) ******* name is " + str(name) + " *************  url is -> "+url
        SearchForTrailer(name, imdbnum, dirmode)
        
elif mode==990:
        print "Mode 990 (Change watched value) ******* name is " + str(name) + " *************  season is -> '"+season+"'"
        ChangeWatched(imdbnum, type, name, season)
 
elif mode==50:
        print ""+url
        TVCATEGORIES(url)

elif mode==51:
        print ""+url
        MOVIECATEGORIES(url)

elif mode==52:
        print ""+url
        MUSICCATEGORIES(url)

elif mode==53:
        print ""+url
        STANDUPCATEGORIES(url)

elif mode==54:
        print ""+url
        OTHERCATEGORIES(url)

elif mode==55:
        print ""+url
        SEARCH(url)

elif mode==56:
        print ""+url
        ICEHOMEPAGE(url)

elif mode==57:
        print ""+url
        FAVOURITES(url)

elif mode==570:
        print ""+url
        TV_FAVOURITES(url)

elif mode==571:
        print ""+url
        MOVIE_FAVOURITES(url)

elif mode==58:
        print ""+url
        CLEAR_FAVOURITES(url)

elif mode==60:
        print ""+url
        RECENT(url)

elif mode==61:
        print ""+url
        LATEST(url)

elif mode==62:
        print ""+url
        WATCHINGNOW(url)

elif mode==63:
        print ""+url
        HD720pCat(url)
        
elif mode==64:
        print ""+url
        Genres(url)

elif mode==70:
        print ""+url
        Action(url)

elif mode==71:
        print ""+url
        Animation(url)

elif mode==72:
        print ""+url
        Comedy(url)

elif mode==73:
        print ""+url
        Documentary(url)

elif mode==74:
        print ""+url
        Drama(url)

elif mode==75:
        print ""+url
        Family(url)

elif mode==76:
        print ""+url
        Horror(url)

elif mode==77:
        print ""+url
        Romance(url)

elif mode==78:
        print ""+url
        SciFi(url)

elif mode==79:
        print ""+url
        Thriller(url)
    
elif mode==1:
        print ""+url
        MOVIEA2ZDirectories(url)

elif mode==2:
        print ""+url
        MOVIEINDEX(url)
        
elif mode==10:
        print ""+url
        TVA2ZDirectories(url)

elif mode==11:
        print ""+url
        TVINDEX(url)

elif mode==12:
        print ""+url
        TVSEASONS(url,imdbnum)

elif mode==13:
        print ""+url
        TVEPISODES(name,url,None,imdbnum)

elif mode==99:
        print ""+url
        CAPTCHAENTER(url)
        
elif mode==100:
        print ""+url
        LOADMIRRORS(url)

elif mode==101:
        print ""+url
        DVDRip(url)

elif mode==102:
        print ""+url
        HD720p(url)

elif mode==103:
        print ""+url
        DVDScreener(url)

elif mode==104:
        print ""+url
        R5R6(url)

elif mode==110:
        # if you dont use the "url", "name" params() then you need to define the value# along with the other params.
        ADD_TO_FAVOURITES(name,url,imdbnum)

elif mode==111:
        print ""+url
        DELETE_FROM_FAVOURITES(name,url)

elif mode==200:
        print ""+url
        Stream_Source(name,url)

elif mode==201:
        Download_Source(name,url)

elif mode==202:
        Check_Mega_Limits(name,url)

elif mode==203:
        Kill_Streaming(name,url)

elif mode==205:
        PlayFile(name,url)
  
elif mode==300:
        toggleLibraryMode()

xbmcplugin.endOfDirectory(int(sys.argv[1]))
