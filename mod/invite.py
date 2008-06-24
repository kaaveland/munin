"""
Loadable.Loadable subclass
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

# Removed alliance specific things from this module.
# qebab, 24/6/08.

class invite(loadable.loadable):
    def __init__(self,client,conn,cursor):
        loadable.loadable.__init__(self,client,conn,cursor,100)
        self.commandre=re.compile(r"^"+self.__class__.__name__+"(.*)")
        self.paramre=re.compile(r"^\s+(\S+)")
        self.usage=self.__class__.__name__ + " <gimp>"
        self.helptext=["This command adds a recruit to the private channel and gives them access to me. Since this is done automatically, make sure P is online and responding before you do this. You should also make sure that you correctly typed the person's pnick when you sponsored them."]

    def execute(self,nick,username,host,target,prefix,command,user,access):
        m=self.commandre.search(command)
        if not m:
            return 0



        if access < self.level:
            self.client.reply(prefix,nick,target,"You do not have enough access to use this command")
            return 0
        if not user:
            self.client.reply(prefix,nick,target,"You must be registered to use the "+self.__class__.__name__+" command (log in with P and set mode +x)")        
            return 0
        m=self.paramre.search(m.group(1))
        
        if not m:
            self.client.reply(prefix,nick,target,"Usage: %s" % (self.usage,))
            return 0

        # assign param variables 
        gimp=m.group(1)

        query="SELECT * FROM invite(%s,%s)"# AS t1(success BOOLEAN, retmessage TEXT)"
        self.cursor.execute(query,(user,gimp))
        
        res=self.cursor.dictfetchone()
        
        if res['success']:
            # msg p adduser
            # msg p modinfo automode
            self.client.privmsg('P',"adduser #%s %s 399" %(self.config.get('Auth', 'home'), gimp,));
            self.client.privmsg('P',"modinfo #%s automode %s op" %(self.config.get('Auth', 'home'), gimp,));
            reply="You have successfully invited '%s'. The gimp is now your responsibility. If they fuck up and didn't know, it's your fault. So teach them well." % (gimp,)
            #reply="You have sponsored '%s'. In 36 hours you may use the !invite command to make them a member. It is your responsibility to get feedback about their suitability as a member in this period" % (gimp,)
        else:
            reply="You may not invite '%s'. Reason: %s"%(gimp,res['retmessage'])
        self.client.reply(prefix,nick,target,reply)
                                                                    

        # do stuff here

        return 1