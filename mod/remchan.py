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

# This module doesn't have anything alliance specific.
# qebab, 24/6/08.

class remchan(loadable.loadable):
    def __init__(self,client,conn,cursor):
        loadable.loadable.__init__(self,client,conn,cursor,100)
        self.paramre=re.compile(r"^\s+(#\S+)")
        self.usage=self.__class__.__name__ + " <channels>"

    def execute(self,nick,username,host,target,prefix,command,user,access,irc_msg):
        m=self.commandre.search(command)
        if not m:
            return 0
        
        m=self.paramre.search(m.group(1))
        if not m:
            self.client.reply(prefix,nick,target,"Usage: %s" % (self.usage,))
            return 0
        
        chan=m.group(1).lower()         
        
        if access < self.level:
            self.client.reply(prefix,nick,target,"You do not have enough access to remove channels")
            return 0
        
        
        query="SELECT chan,userlevel FROM channel_list WHERE chan=%s LIMIT 1"
        self.cursor.execute(query,(chan,))
        res=self.cursor.dictfetchone()
        if not res:
            self.client.reply(prefix,nick,target,"Channel '%s' does not exist" % (chan,))
            return 0
        access_lvl = res['userlevel']
        real_chan = res['chan']
        
        if access_lvl >= access:
            self.client.reply(prefix,nick,target,"You may not remove %s, the channel's access (%s) exceeds your own (%s)" % (real_chan, access_lvl, access))
            return 0
        
        query="DELETE FROM channel_list WHERE chan=%s"
        
        try:
            self.cursor.execute(query,(real_chan,))
            if self.cursor.rowcount>0:
                self.client.privmsg('P',"remuser %s %s" %(real_chan, self.config.get('Connection', 'nick')))
                self.client.wline("PART %s" % (real_chan,))
                self.client.reply(prefix,nick,target,"Removed channel %s" % (real_chan,))
            else:
                self.client.reply(prefix,nick,target,"No channel removed" )
        except:
            raise
        
        return 1
        
            
