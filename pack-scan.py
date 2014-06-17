#!/usr/bin/env python
import sys
import time
import gettext
import optparse
import commands
import subprocess
import re

_ = gettext.gettext

class PackScanCli(object):
    def __init__(self):
        self.cols = []
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
        if not args:
            args = sys.argv[1:]

        self.options, self.args = self.parser.parse_args(args)

        if hasattr(self.options, "user_host") and self.options.user_host:
            try:
                self.user, host = self.options.user_host
                print 'user: %s\nhost: %s' % (self.user, host)
                self.ssh = True
            except ValueError, e:
                print 'Invalid input please try again'
                exit(1)
        else:
            host = self.run_com('hostname')[1].strip()
        release = self.run_com('cat /etc/redhat-release')[1].strip()

        output = self.run_com('rpm -qa --qf "%{NAME}|'
            '%{VERSION}|'
            '%{RELEASE}|'
            '%{INSTALLTIME}|'
            '%{VENDOR}|'
            '%{BUILDTIME}|'
            '%{BUILDHOST}|'
            '%{SOURCERPM}|'
            '%{LICENSE}|%'
            '{PACKAGER}\n"')[1]

        installed_packages = [PkgInfo(x) for x in output.splitlines()]
        rh_packages = filter(PkgInfo.is_red_hat_pkg, installed_packages)
        greatest = max(rh_packages, key= lambda x: x.install_time)
        greatest, greatest_build = reduce(self.update_info, rh_packages, (None, None))

        curr_date = self.run_com('date +%s')[1].strip()
        result = "%s (%s)  -  %s" % (host, release, curr_date)
        result += "\nRed Hat (Y/N), "
        if (len(rh_packages) > 0):
            result += "Y"
            result += "\nRH Pkgs, %s/%s" % (len(rh_packages), len(installed_packages))
            result += "\nLast Installed, "
            result += self.details_install(greatest)

            result += "\nLast Built, %s" % self.details_built(greatest_build)
        else:
            result += "N"
        result += "\nVirt-What installed (Y/N), "
        if self.run_com('command -v virt-what')[1].strip():
            result += "Y"
            exitcode, virt_what_output = self.run_com('sudo virt-what')  # Virt-what needs to run as root
            if exitcode == 0:
                if virt_what_output:
                # Writes all virt-what facts to the output as a double quoted field. 
                result += '\nVirt-what Facts, "%s"' % virt_what_output.rstrip().replace('\n', ', ')
        else:
            result += "N"

        self.save_results(result, host)

    def update_info(self, vals, pkg):
        greatest, greatest_build = vals  # unpack the values as given by the initial call to reduce
        if pkg and pkg.is_red_hat:
            if greatest == None:
                greatest = pkg
            elif greatest.install_time < pkg.install_time:
                greatest = pkg
            if greatest_build == None:
                greatest_build = pkg
            elif greatest_build.build_time < pkg.build_time:
                greatest_build = pkg
        return (greatest, greatest_build)

    def save_results(self, output, host):
        with open('%s.csv' % host, 'w') as f:
            f.write(output)
        subprocess.call(["zip", "%s.zip" % host, "%s.csv" % host])
        subprocess.call(["rm", "%s.csv" % host])
        if not self.ssh:
            print "Please submit %s.zip\n" % host

    # Ensures the command is run on the appropriate machine
    def run_com(self, com):
        if self.ssh:
            command = "ssh %s@%s '%s'" % (self.user, host, com)
            return commands.getstatusoutput(command)
        else:
            return commands.getstatusoutput(com)

    def details_built(self, pkg):
        details = "%s-%s-%s" % (pkg.name, pkg.version, pkg.release)
        local_time = time.localtime(float(pkg.build_time))
        details += " Built: %s" % time.strftime("%x %X",local_time)
        return details

    def details_install(self, pkg):
        details = "%s-%s-%s" % (pkg.name, pkg.version, pkg.release)
        local_time = time.localtime(float(pkg.install_time))
        details += " Installed: %s" % time.strftime("%x %X",local_time)
        return details

    def add_options(self):
        self.parser.add_option("-r", "--remote", help=_("Executes pack-scan using ssh for the given [USER HOST]"), dest="user_host", default=None, nargs=2)
        self.parser.add_option("-f", "--file", help=_("File of [USER HOST] to run the tool against."), dest="file")


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


if __name__ == '__main__':
    PackScanCli()
