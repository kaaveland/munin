import munin.irc_message as irc_message
import os

class command(object):
    def __init__(self,client,cursor,module,loader,reboot):
        self.client=client
        self.cursor=cursor
        self.module=module
        self.reboot=reboot
        self.control=self.register_control(module,loader)

    def register_control(self,module,loader):
        modules=loader.get_submodules(module.__name__)
        result={}
        for m in modules:
            result[m.__name__]=getattr(m,m.__name__.split('.')[-1])(self.cursor)
        return result


    def message(self,line):
        irc_msg = irc_message.irc_message(client = self.client,
                                          cursor = self.cursor,
                                          line   = line)
        if irc_msg.command:
            key = "munin.mod."+irc_msg.command_name
            if self.control.has_key(key):
                try:
                    self.control[key].execute(irc_msg.user,irc_msg.access,irc_msg)
                except Exception, e:
                    irc_msg.reply("Error in module '%s'. Please report the command you used to the bot owner as soon as possible."%(irc_msg.command_name,))
                    raise e
                self.log_command(irc_msg)
            elif key == 'munin.mod.help':
                self.help(irc_msg)
            elif key == 'munin.mod.reboot' and irc_msg.access >= 1000:
                self.reboot()


    def log_command(self,irc_msg):
        if irc_msg.command.lower() == 'pref':
            return
        query="INSERT INTO command_log (command_prefix,command,command_parameters,nick,pnick,username,hostname,target)"
        query+=" VALUES"
        query+=" (%s,%s,%s,%s,%s,%s,%s,%s)"

        self.cursor.execute(query,(irc_msg.prefix,
                                   irc_msg.command_name,
                                   irc_msg.command_parameters,
                                   irc_msg.nick,
                                   irc_msg.user,
                                   irc_msg.username,
                                   irc_msg.host,
                                   irc_msg.target))

    def help(self,irc_msg):
        if irc_msg.command_parameters:
            key = 'munin.mod.'+irc_msg.command_parameters
            if self.control.has_key(key):
                self.control[key].help(irc_msg.user,irc_msg.access,irc_msg)
            else:
                irc_msg.reply("No command matching '%s'"%irc_msg.command_parameters)
        else:
            irc_msg.reply("Munin help. For more information use: <"+irc_msg.notprefix.replace("|","")+irc_msg.pubprefix.replace("|","")+irc_msg.privprefix.replace("|","")+">help <command>. Built-in commands: help")
            command_list = map(lambda x: x.__class__.__name__,self.control.values())
            command_list.sort()
            command_list = ", ".join(command_list)
            irc_msg.reply(command_list)
        pass

