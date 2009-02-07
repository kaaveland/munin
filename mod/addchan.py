"""
Loadable subclass
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

# This file has no alliance specific stuff as far as I can tell.
# qebab, 22/06/08

class addchan(loadable.loadable):
    def __init__(self,client,conn,cursor):
        loadable.loadable.__init__(self,client,conn,cursor,500)
        self.paramre=re.compile(r"^\s+(#\S+)\s+(\d+)")
        self.usage=self.__class__.__name__ + " <chan> <level>"

    
    def execute(self,nick,username,host,target,prefix,command,user,access,irc_msg):
        m=self.commandre.search(command)
        if not m:
            return 0
        m=self.paramre.search(m.group(1))
        if not m:
            self.client.reply(prefix,nick,target,"Usage: %s" % (self.usage,))
            return 0
        
        chan=m.group(1).lower()
        access_lvl=int(m.group(2))

        if access < self.level:
            self.client.reply(prefix,nick,target,"You do not have enough access to add new channels")
            return 0
        
        if access_lvl >= access:
            self.client.reply(prefix,nick,target,"You may not add a channel with equal or higher access to your own")
            return 0
        
        query="INSERT INTO channel_list (chan,userlevel,maxlevel) VALUES (%s,%s,%s)"
        
        try:
            self.cursor.execute(query,(chan,access_lvl,access_lvl))
            if self.cursor.rowcount>0:
                self.client.reply(prefix,nick,target,"Added chan %s at level %s" % (chan,access_lvl))
                self.client.privmsg('P',"set %s autoinvite on" %(chan,));
                self.client.privmsg('P',"invite %s" %(chan,));
                        
        except psycopg.IntegrityError:
            self.client.reply(prefix,nick,target,"Channel %s already exists" % (chan,))
            return 0
        except:
            raise

        return 1
