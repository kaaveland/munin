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

class galmate(loadable.loadable):
    def __init__(self,client,conn,cursor):
        loadable.loadable.__init__(self,client,conn,cursor,500)
        self.paramre=re.compile(r"^\s+(\S+)")
        self.usage=self.__class__.__name__ + " <pnick>"
        self.helptext=None        
    
    def execute(self,nick,username,host,target,prefix,command,user,access):
        m=self.commandre.search(command)
        if not m:
            return 0

        if not user:
            self.client.reply(prefix,nick,target,"You must be registered to use the "+self.__class__.__name__+" command (log in with P and set mode +x)")
            return 1
        
        if access < self.level:
            self.client.reply(prefix,nick,target,"You do not have enough access to add galmates")
            return 0
                        
        
        m=self.paramre.search(m.group(1))
        if not m:
            self.client.reply(prefix,nick,target,"Usage: adduser")
            return 0
        
        pnick=m.group(1).lower()
        
        query="INSERT INTO user_list (pnick,userlevel) VALUES (%s,1)"
        
        try:
            self.cursor.execute(query,(pnick,))
            if self.cursor.rowcount>0:
                self.client.reply(prefix,nick,target,"Added user %s at level 1" % (pnick,))
        except psycopg.IntegrityError:
            self.client.reply(prefix,nick,target,"User %s already exists" % (pnick,))
            return 0
        except:
            raise

        return 1
