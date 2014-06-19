#!/usr/bin/env python
import sys
import time
import optparse
import commands
import subprocess
import re

class PackScanCli(object):
    def __init__(self):
        self.user = None
        self.ssh = False
        self.options = None
        self.args = None
        self.parser = optparse.OptionParser()
        self.add_options()
        self.main()

    def main(self, args=None):

        if not args:
            args = sys.argv[1:]

        self.options, self.args = self.parser.parse_args(args)
        if hasattr(self.options, "filename") and self.options.filename:
            PackScanFileCmd(self.options.filename).main()
        elif hasattr(self.options, "user_host") and self.options.user_host:
            try:
                user, host = self.options.user_host
            except ValueError, e:
                print 'Invalid input. Please try again.'
                exit(1)
            PackScanUserHostCmd(user, host).main()
        else:
            PackScanCmd().main()


    def add_options(self):
        self.parser.add_option("-r", "--remote", help="Executes pack-scan using ssh for the given [USER HOST]", dest="user_host", default=None, nargs=2)
        self.parser.add_option("-f", "--file", help="File of [USER HOST] to run the tool against.", dest="filename")


# This class contains the information retrieved about and installed package
# as returned by the query using rpm
class PkgInfo(object):
    def __init__(self, row, separator='|'):
        cols = row.split(separator)
        if len(cols) < 10:
            raise PkgInfoParseException()
        else:
            self.name = cols[0]
            self.version = cols[1]
            self.release = cols[2]
            self.install_time = long(cols[3])
            self.vendor = cols[4]
            self.build_time = long(cols[5])
            self.build_host = cols[6]
            self.source_rpm = cols[7]
            self.license = cols[8]
            self.packager = cols[9]
            self.is_red_hat = False
            if ('redhat.com' in self.build_host and
            'fedora' not in self.build_host and
            'rhndev' not in self.build_host):
                self.is_red_hat = True

    def is_red_hat_pkg(self):
        return self.is_red_hat

    def details_built(self):
        details = self.details()
        local_time = time.localtime(float(self.build_time))
        details += " Built: %s" % time.strftime("%x %X",local_time)
        return details

    def details_install(self):
        details = self.details()
        local_time = time.localtime(float(self.install_time))
        details += " Installed: %s" % time.strftime("%x %X",local_time)
        return details

    def details(self):
        return "%s-%s-%s" % (self.name, self.version, self.release)

class PkgInfoParseException(BaseException):
    pass

# As the requirements are similar the following few classes are modelled after RHO's RhoCmd set of classes
# Each class represents an option/command that could be passed to PackScan
class PackScanCmd(object):
    name = "base"
    fields = []

    def __init__(self):
        self.cmd_results = {}
        self.data = {}
        self.exitcode = {}
        self.cmds = {
            "host" : 'hostname',
            "release" : 'cat /etc/redhat-release',
            "rpm_output" :  'rpm -qa --qf "%{NAME}|'
                            '%{VERSION}|'
                            '%{RELEASE}|'
                            '%{INSTALLTIME}|'
                            '%{VENDOR}|'
                            '%{BUILDTIME}|'
                            '%{BUILDHOST}|'
                            '%{SOURCERPM}|'
                            '%{LICENSE}|%'
                            '{PACKAGER}\n"',
            "date" : 'date',
            "uid" : 'id -u',
            "virt_what_path" : 'command -v virt-what',
            "virt_what" : 'virt-what',
            "dmiinfo" : 'dmidecode -t 4',
        }

    def populate_data(self):
        for var, cmd in self.cmds.iteritems():
            self.exitcode[var], self.cmd_results[var] = self.run_cmd(cmd)
        # self.parse_data()

    def parse_data(self):
        for key, value in self.cmd_results.iteritems():
            setattr(self, key, value.strip())

    def run_cmd(self, cmd):
        return commands.getstatusoutput(cmd)

    def main(self):
        self.populate_data()
        PackScanCmd.save_results(SystemReport(self.cmd_results))

    @staticmethod
    def save_results(report):
        filename = '%s.csv' % report.host
        try:
            f = open(filename, 'w')
            f.write(str(report))
            f.close()
        except EnvironmentError, e:
            sys.stderr.write('Error writing to %s: %s\n' % (filename, e))
            f.close()
        subprocess.call(["zip", "%s.zip" % report.host, "%s.csv" % report.host])
        subprocess.call(["rm", "%s.csv" % report.host])

class PackScanUserHostCmd(PackScanCmd):
    name = "user_host"

    def __init__(self, user, host):
        super(PackScanUserHostCmd, self).__init__()

        # Host will be passed in in the case of this command and need not be run remotely
        del self.cmds['host']
        self.user = user
        self.cmd_results['host'] = host


    def run_cmd(self, cmd):
        command = "ssh %s@%s '%s'" % (self.user, self.cmd_results['host'], cmd)
        exitcode, result = commands.getstatusoutput(command)
        print exitcode
        if exitcode != '0':
            print "Connection via SSH failed"
            return (exitcode, "Connection via SSH failed")
        else:
            return (exitcode, result)

class PackScanFileCmd(PackScanUserHostCmd):
    name = "file"

    def __init__(self, filename):
        self.user_hosts = []
        self.filename = filename
        self.parse_file()

    def parse_file(self):
        try:
            f = open(self.filename, 'r')
            self.user_hosts = [line.strip().split(' ') for line in f.readlines()]
            f.close()
        except EnvironmentError, e:
            sys.stderr.write('Error writing to %s: %s\n' % (filename, e))
            f.close()

    def main(self):
        [PackScanUserHostCmd(x,y).main() for x,y in self.user_hosts]


class SystemReport(object):
    """The SystemReport class represents a report on a system with the given data"""
    # This is a dict of fields and functions that will return the appropriate string value for the field
    not_root_msg = "Not root"
    def __init__(self, data, seperator=","):
        self.data = data
        self.seperator = seperator
        self.fields = [
            ["Red Hat (Y/N)" , self.is_red_hat],
            ["RH Pkgs" , self.rhpkgs],
            ["Last Installed" , self.last_installed],
            ["Last Built" , self.last_built],
            ["Virt Host Info" , self.virt_host],
            ["Sockets" , self.sockets],
            ["Cores" , self.cores,]
        ]

        self.parse_data()
        try:
            self.installed_packages = [PkgInfo(line) for line in self.rpm_output.splitlines()]
        except PkgInfoParseException, e:
            print "Failed to parse info from RPM"
            self.installed_packages = {}
        self.rh_packages = filter(PkgInfo.is_red_hat_pkg, self.installed_packages)
        try:
            self.greatest = max(self.rh_packages, key= lambda x: x.install_time)
            self.greatest_build = max(self.rh_packages, key= lambda x: x.build_time)
        except ValueError, e:
            pass


    def __str__(self):
        result = "%s (%s)  -  %s" % (self.host, self.release, self.date)
        try:
            for field, value_func in self.fields:
                result += "\n%s%s %s" % (field, self.seperator, value_func())
        except NotRedHatException, e:
            result += "\nRed Hat (Y/N), N"

        return result

    # adds all items in data as attributes of this instance of SystemReport
    def parse_data(self):
        for key, value in self.data.iteritems():
            setattr(self, key, value.strip())

    def is_red_hat(self):
        if len(self.rh_packages) > 0:
            return "Y"
        else:
            raise NotRedHatException()

    def rhpkgs(self):
        return "%s/%s" % (len(self.rh_packages), len(self.installed_packages))

    def last_installed(self):
        return self.greatest.details_install()

    def last_built(self):
        return self.greatest_build.details_built()

    def virt_host(self):
        if self.uid !='0':
            return self.not_root_msg
        elif hasattr(self, "virt_what_path") and len(self.virt_what_path) == 0:
            return "virt-what missing"
        elif self.virt_what:
            return '"%s"' % self.virt_what.replace('\n', ', ')
        elif self.virt_what == "":
            return "Baremetal"
        else:
            return "Error running virt-what"

    def sockets(self):
        if self.uid != '0':
            return self.not_root_msg
        else:
            return len(re.findall('Socket Designation', self.dmiinfo))

    def cores(self):
        if self.uid != '0':
            return self.not_root_msg
        else:
            core_count_match = re.findall('Core Count: ([0-9]+)', self.dmiinfo)
            num_cores = sum([int(x) for x in core_count_match])
            return num_cores

class NotRedHatException(BaseException):
    pass

if __name__ == '__main__':
    PackScanCli()
