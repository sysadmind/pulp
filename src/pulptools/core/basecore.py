#
# Base class inherited by all cores
#
# Copyright (c) 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#

import os
import sys
from optparse import OptionParser
import pulptools.utils as utils


class BaseCore(object):
    """ Base class for all sub-calls. """
    def __init__(self, name="cli", usage=None, shortdesc=None,
            description=None):
        self.shortdesc = shortdesc
        if shortdesc is not None and description is None:
            description = shortdesc
        self.debug = 0
        self.setup_option_parser(usage, description, False)
        self.generate_options()
        self._add_common_options()
        self.name = name
        self.username = None
        self.password = None

    def setup_option_parser(self, usage, description, skip_actions):
        self.usage = "usage: %prog -u <username> -p <password> " + usage
        self.parser = OptionParser(usage=self._usage_str(skip_actions), 
                                   description=description)
        

    def _add_common_options(self):
        """ Common options to all modules. """
        help = "username for access to Pulp."  
        help = help + "  Default user admin is included with base install."
        self.parser.add_option("-u", "--username", dest="username",
                       help=help)
        help = "password for access to Pulp."  
        self.parser.add_option("-p", "--password", dest="password",
                       help=help)
        

    def _get_action(self):
        """ Validate the arguments passed in and determine what action to take """
        action = None
        possiblecmd = utils.findSysvArgs(sys.argv)
        if len(possiblecmd) > 2:
            action = possiblecmd[2]
        elif len(possiblecmd) == 2 and possiblecmd[1] == self.name:
            self._usage()
            sys.exit(0)
        else:
            return None 
        if action not in self.actions.keys():
            self._usage()
            sys.exit(0)
        return action 
    
    def generate_options(self):
        pass
    
    def _usage_str(self, skip_actions):
        retval = self.usage.replace("%prog", os.path.basename(sys.argv[0])) + "\n"
        if (not skip_actions):
            retval = retval + "Supported Actions:\n"
            items = self.actions.items()
            items.sort()
            for (name, cmd) in items:
                retval = retval + "\t%-14s %-25s\n" % (name, cmd)
        return retval
    
    def _usage_old(self):
        print "\nUsage: %s MODULENAME ACTION [options] --help\n" % os.path.basename(sys.argv[0])
        print "Supported Actions:\n"
        items = self.actions.items()
        items.sort()
        for (name, cmd) in items:
            print("\t%-14s %-25s" % (name, cmd))
        print("")

    def _usage(self):
        print self._usage_str(False)

    def _do_core(self):
        # Subclass required to implement to actually execute the indicated command
        pass
    
    def load_server(self):
        # Subclass required to implement to setup Connection to Pulp server
        pass
    
    def main(self):
        (self.options, self.args) = self.parser.parse_args()
        self.username = self.options.username
        self.password = self.options.password
        self.load_server()
        self._do_core()

def systemExit(code, msgs=None):
    "Exit with a code and optional message(s). Saved a few lines of code."

    if msgs:
        if type(msgs) not in [type([]), type(())]:
            msgs = (msgs, )
        for msg in msgs:
            sys.stderr.write(unicode(msg).encode("utf-8") + '\n')
    sys.exit(code)