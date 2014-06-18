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
        #TODO: Add arg parsing for list of hosts to cover functionality of pack-scan-ssh.pl
        #TODO: Add file read in functionality

        test = PackScanCmd()
        test.main()

    def add_options(self):
        self.parser.add_option("-r", "--remote", help="Executes pack-scan using ssh for the given [USER HOST]", dest="user_host", default=None, nargs=2)
        self.parser.add_option("-f", "--file", help="File of [USER HOST] to run the tool against.", dest="file")


# This class contains the information retrieved about and installed package
# as returned by the query using rpm
class PkgInfo(object):
    def __init__(self, row, separator='|'):
        cols = row.split(separator)
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
        self.parse_data()

    def parse_data(self):
        for key, value in self.cmd_results.iteritems():
            setattr(self, key, value.strip())

    def run_cmd(self, cmd):
        return commands.getstatusoutput(cmd)

    def main(self):
        self.populate_data()

        installed_packages = [PkgInfo(line) for line in self.rpm_output.splitlines()]
        rh_packages = filter(PkgInfo.is_red_hat_pkg, installed_packages)
        greatest = max(rh_packages, key= lambda x: x.install_time)
        greatest_build = max(rh_packages, key= lambda x: x.build_time)

        result = "%s (%s)  -  %s" % (self.host, self.release, self.date)
        result += "\nRed Hat (Y/N), "
        if (len(rh_packages) > 0):
            result += "Y"
            result += "\nRH Pkgs, %s/%s" % (len(rh_packages), len(installed_packages))
            result += "\nLast Installed, "
            result += greatest.details_install()

            result += "\nLast Built, %s" % greatest_build.details_built()
        else:
            result += "N"
        if self.uid != '0':
            result += "\nvirt.is_guest, Not run as root"
            result += "\nvirt.host_type, Not run as root"
            result += "\nDmi Info, Not run as root"
        else:
            result += "\nVirt-What installed (Y/N), "

            if self.virt_what_path:
                result += "Y"
                if self.exitcode['virt_what'] == 0:
                    if self.virt_what:
                        # Writes all virt-what facts to the output as a double quoted field.
                        result += '\nVirt-what Facts, "%s"' % self.virt_what.replace('\n', ', ')
                    else:
                        result += '\nVirt Host, None'
            else:
                result += "N"
        self.save_results(result, self.host)

    def save_results(self, output, host):
        filename = '%s.csv' % host
        try:
            f = open(filename, 'w')
            f.write(output)
            f.close()
        except EnvironmentError, e:
            sys.stderr.write('Error writing to %s: %s\n' % (filename, e))
            f.close()
        subprocess.call(["zip", "%s.zip" % host, "%s.csv" % host])
        subprocess.call(["rm", "%s.csv" % host])




if __name__ == '__main__':
    PackScanCli()
