"""
Parser class 
"""

# This file is part of Munin.

# Munin is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# Munin is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Munin; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

# This work is Copyright (C)2006 by Andreas Jacobsen 
# Individual portions may be copyright by individual contributors, and
# are included in this collective work with permission of the copyright 
# owners.

import re
import psycopg
import sys
sys.path.insert(0, "custom")
import os
import traceback
import string
import math
import loadable 
import scan
import galstatus

DEBUG = 1

# This is such a beast...

class parser:
    def __init__(self, config, client, irc):
        # Private variables
        self.notprefix=r"~|-|\."
        self.pubprefix=r"!"
        self.privprefix='@'
        self.client=client
        self.irc=irc
        self.ctrl_list={}
        self.config = config

        #database variables (also private)
        self.mod_dir="mod"
        self.user=config.get("Database", "user")
        self.dbname=config.get("Database", "dbname")
        self.dsn = 'user=%s dbname=%s' % (self.user, self.dbname)
        if config.has_option("Database", "password"):
            self.dsn += ' password=%s' % config.get("Database", "password")
        # database connection and cursor
        self.conn=psycopg.connect(self.dsn)
        self.conn.serialize()
        self.conn.autocommit()
        self.cursor=self.conn.cursor()

        self.galstatus=galstatus.galstatus(self.client,self.conn,self.cursor)
        
        # Necessary regexps (still private)
        self.welcomre=re.compile(r"\S+\s+001.*",re.I)
        
        # obey P
        self.pinvitere=re.compile(r":P!cservice@netgamers.org\s+INVITE\s+\S+\s+:#(\S+)",re.I)
        
        # privmsg command regexes
        self.privmsgre=re.compile(r":(\S+)!(\S+)@(\S+)\s+PRIVMSG\s+(\S+)\s+:(.*)")
        self.ischannelre=re.compile(r"(#\S+)")
        
        self.pnickre=re.compile(r"(\S{2,15})\.users\.netgamers\.org")

        self.reg_controllers()
        
        #self.commandre=re.compile(r"(%s|%s)(\S+)\s+(.*)\s*$" % (self.pubprefix,self.privprefix))
        self.commandre=re.compile(r"^(%s|%s|%s)(.*)\s*$" % (self.notprefix,self.pubprefix,self.privprefix))
        self.loadmodre=re.compile(r"^loadmod\s+(\S+)")
        self.helpre=re.compile(r"^help(\s+(\S+))?")
        #self.addmoduserre=re.compile(r"(\S{1,5})\s+(\d+)\s*$")
        #self.addmodchanre=re.compile(r"(#\S+)\s+(\d+)\s*$")
        #self.remuserre=re.compile(r"^(\S{1,15})\s*$")
        #self.remchanre=re.compile(r"^(#\S+)\s*$")
        #self.addremtargtypere=re.compile(r"^(\S+)\s*$")
        #self.addtargre=re.compile(r"^(\d{1,3}):(\d{1,2}):(\d{1,2})$")
        #self.taketargre=re.compile(r"^(\d{1,3}):(\d{1,2}):(\d{1,2})$")
        #self.modtargre=re.compile(r"^(\d+) ?(.*)\s*")
        #self.remtargre=re.compile(r"^(\d{1,3}):(\d{1,2}):(\d{1,2})\s*")
        #self.coordre=re.compile(r"^(\d{1,3}):(\d{1,2}):(\d{1,2})$")
        
        
        self.scanre=re.compile("http://[^/]+/showscan.pl\?scan_id=(\d+)")
        self.scangrpre=re.compile("http://[^/]+/showscan.pl\?scan_grp=(\d+)")
    def parse(self,line):
        m=self.welcomre.search(line)
        if m:
            self.client.wline("PRIVMSG P@cservice.netgamers.org :auth %s" % (self.config.get("IRC", "auth")))
            self.client.wline("MODE %s +%s" % (self.irc.nick, self.config.get("IRC", "modes")))
            return None
        m=self.pinvitere.search(line)
        if m:
            self.client.wline("JOIN #%s" % m.group(1))
            return None
        m=self.privmsgre.search(line);
        if m:
            nick=m.group(1).lower()
            username=m.group(2).lower()
            host=m.group(3).lower()
            target=m.group(4).lower()
            message=m.group(5)

            user=self.getpnick(host)

            #print "running scan parse"
            for m in self.scanre.finditer(message):
                self.scan(m.group(1),nick,user,None)
                pass
            for m in self.scangrpre.finditer(message):
                self.scan(None, nick, user, m.group(1))
                pass
            self.galstatus.parse(message,nick,user,target)
            
            m=self.commandre.search(message)
            if not m:
                return None
            prefix=m.group(1)
            command=m.group(2)
            

            query="SELECT * FROM access_level(%s,%s)"
            self.cursor.execute(query,(user,target))
            access=self.cursor.dictfetchone()['access_level'] or 0
            print "access: %d, user: %s, #channel: %s"%(access,user,target)
            
            com_list = command.split(' ',1)
            
            if command.lower() != 'pref' and len(com_list) > 0:
                query="INSERT INTO command_log (command_prefix,command,command_parameters,nick,pnick,username,hostname,target)"
                query+=" VALUES"
                query+=" (%s,%s,%s,%s,%s,%s,%s,%s)"
                
                command_command = com_list[0]
                command_parameters = None
                if len(com_list) > 1:
                    command_parameters = com_list[1]
                try:
                    self.cursor.execute(query,(prefix,command_command,command_parameters,nick,user,username,host,target))
                except Exception, e:
                    print "Exception during command logger: " + e.__str__()
                    
            
            if access > 0:
                m=self.loadmodre.search(command)
                if m:
                    if access < 1000:
                        self.client.reply(self.prefix_to_numeric(prefix),nick,target,"Fuck off twat")
                        return None
                    mod_name=m.group(1)
                    err_msg=self.load_mod(mod_name)
                    if err_msg:
                        self.client.reply(self.prefix_to_numeric(prefix),nick,target,"Failed to load module '%s' with reason: '%s'" % (mod_name,err_msg))
                    else:
                        self.client.reply(self.prefix_to_numeric(prefix),nick,target,"Successfully loaded module '%s'" % (mod_name,))
                    return "Successfully loaded module '%s'" % (mod_name,)



                m=self.helpre.search(command)
                if m:
                    return self.help(nick,username,host,target,message,self.prefix_to_numeric(prefix),command,user,access,m.group(2))
                
                return self.run_commands(nick,username,host,target,message,prefix,command,user,access)
                            
                            
                #do stuff!
        return None

    def scan(self, rand_id,nick,pnick, group_id):
        s = scan.scan(rand_id,self.client,self.conn,self.cursor,nick,pnick, group_id)
        s.run()

    # split off parse into a func?

    def run_commands(self,nick,username,host,target,message,prefix,command,user,access):
        #if self.ctrl_list.has_key(command):
        #    k=command

        for k in self.ctrl_list.keys():
            ctrl=self.ctrl_list[k]
            #print "Trying key %s with obj of class '%s'" % (k,ctrl.__class__.__name__)
            
            try:
                if ctrl.execute(nick,username,host,target,self.prefix_to_numeric(prefix),command,user,access):
                    return "Successfully executed command '%s' with key '%s'" % (ctrl.__class__.__name__,k)
            except Exception, e:
                del self.ctrl_list[k]
                print "Exception in "+ ctrl.__class__.__name__ +" module dumped"
                self.client.reply(self.prefix_to_numeric(prefix),nick,target,"Error in module '"+ ctrl.__class__.__name__ +"'. Please report the command you used to jester as soon as possible.")
                print e.__str__()
                traceback.print_exc()
                if DEBUG:
                    print "nick: '%s'" % (nick,)
                    print "username: '%s'" % (username,)
                    print "host: '%s'" % (host,)
                    print "target: '%s'" % (target,)
                    print "message: '%s'" % (message,)
                    print "prefix: '%s'" % (prefix,)
                    print "command: '%s'" % (command,)
                    print "user: '%s'" % (user,)
                    print "access: '%s'" % (access,)
                    err_msg=self.load_mod(k)
                    if err_msg:
                        self.client.reply(self.prefix_to_numeric(prefix),nick,target,"Unable to reload module '%s', this may seriously impede further use" % (k,))
                        print err_msg
        return None

    def load_mod(self,mod_name):
        try:
            if mod_name == 'loadable':
                loadable = reload(sys.modules['loadable'])
                self.reg_controllers()
                return None
            if mod_name == 'scan':
                scan = reload(sys.modules['scan'])
                return None
            if mod_name == 'galstatus':
                galstatus = reload(sys.modules['galstatus'])
                self.galstatus=galstatus.galstatus(self.client,self.conn,self.cursor)
                return None
            filename=os.path.join(self.mod_dir,mod_name+'.py')
            execfile(filename)
            self.ctrl_list[mod_name] = locals().get(mod_name)(self.client,self.conn,self.cursor)
        except Exception, e:
            traceback.print_exc()
            return e.__str__()

        return None

    def help(self,nick,username,host,target,message,prefix,command,user,access,param):
        if param:
            if self.ctrl_list.has_key(param):
                if access >= self.ctrl_list[param].level:
                    try:
                        #self.client.reply(prefix,nick,target,param+": "+self.ctrl_list[param].help())
                        self.ctrl_list[param].help(nick,username,host,target,prefix,user,access)
                        return "Successfully executed help for '%s' with key '%s'" % (self.ctrl_list[param].__class__.__name__,param)
                    except Exception, e:
                        ctrl=self.ctrl_list[param]
                        del self.ctrl_list[param]
                        print "Exception in "+ ctrl.__class__.__name__ +" module dumped"
                        self.client.reply(prefix,nick,target,"Error in module '"+ ctrl.__class__.__name__ +"'. Please report the command you used to jester as soon as possible.")
                        print e.__str__()
                        traceback.print_exc()
                        if DEBUG:
                            print "nick: '%s'" % (nick,)
                            print "username: '%s'" % (username,)
                            print "host: '%s'" % (host,)
                            print "target: '%s'" % (target,)
                            print "message: '%s'" % (message,)
                            print "prefix: '%s'" % (prefix,)
                            print "command: '%s'" % (command,)
                            print "user: '%s'" % (user,)
                            print "access: '%s'" % (access,)
                            err_msg=self.load_mod(param)
                            if err_msg:
                                self.client.reply(prefix,nick,target,"Unable to reload module '%s', this may seriously impede further use" % (k,))
                                print err_msg
                        return
        self.client.reply(prefix,nick,target,
                          "Munin help. For more information use: <"+self.notprefix.replace("|","")+self.pubprefix.replace("|","")+self.privprefix.replace("|","")+">help <command>. Built-in commands: help" + (bool(access>=1000) and ", loadmod" or ""))
        command_list=[]
        for ctrl in self.ctrl_list.values():
            if access >= ctrl.level:
                command_list.append(ctrl.__class__.__name__)
        command_list.sort()
        self.client.reply(prefix,nick,target,"Loaded modules: "+ ", ".join(command_list))
        
                          
    def getpnick(self,host):
        m=self.pnickre.search(host)
        if m:
            return m.group(1).lower()
        else:
            return None
        
    def get_user_access(self,pnick):
        query="SELECT userlevel FROM user_list WHERE pnick=%s"
        
        user_found=self.cursor.execute(query,(pnick,))
        result=self.cursor.fetchone()
        if result:
            return result[0]
        else:
            return 0
        
    def get_chan_access(self,channel):
        query="SELECT userlevel FROM channel_list WHERE chan=%s"
        self.cursor.execute(query,(channel,))
        result=self.cursor.fetchone()
        if result:
            return result[0]
        else:
            return 0

    def reg_controllers(self):
        for command_name in os.listdir(self.mod_dir):
            m=re.search("(.*)\.py$",command_name,re.I)
            if m:
                source=m.group(1)
                if source != "__init__":
                    filename=os.path.join(self.mod_dir, source+'.py')
                    execfile(filename)
                    self.ctrl_list[source] = locals().get(source)(self.client,self.conn,self.cursor)


                
    def prefix_to_numeric(self,prefix):
        if self.notprefix.replace("|","").find(prefix) > -1:
            return self.client.NOTICE_PREFIX
        if self.pubprefix.replace("|","").find(prefix) > -1:
            return self.client.PUBLIC_PREFIX
        if self.privprefix.replace("|","").find(prefix) > -1:
            return self.client.PRIVATE_PREFIX        
        return -1