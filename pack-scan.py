#!/usr/bin/env python
import sys
import time
import optparse
import commands
import subprocess
import re

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

        installed_packages = [PkgInfo(line) for line in output.splitlines()]
        rh_packages = filter(PkgInfo.is_red_hat_pkg, installed_packages)
        greatest = max(rh_packages, key= lambda x: x.install_time)
        greatest_build = max(rh_packages, key= lambda x: x.build_time)

        curr_date = self.run_com('date +%s')[1].strip()
        result = "%s (%s)  -  %s" % (host, release, curr_date)
        result += "\nRed Hat (Y/N), "
        if (len(rh_packages) > 0):
            result += "Y"
            result += "\nRH Pkgs, %s/%s" % (len(rh_packages), len(installed_packages))
            result += "\nLast Installed, "
            result += greatest.details_install()

            result += "\nLast Built, %s" % greatest_build.details_built()
        else:
            result += "N"
        if self.run_com('id -u')[1] != '0':
            # print self.run_com('id -u')[1]
            result += "\nvirt.is_guest, Not run as root"
            result += "\nvirt.host_type, Not run as root"
            result += "\nDmi Info, Not run as root"
        else:
            result += "\nVirt-What installed (Y/N), "

            if self.run_com('command -v virt-what')[1].strip():
                result += "Y"
                exitcode, virt_what_output = self.run_com('virt-what')
                print virt_what_output
                if exitcode == 0:
                    print virt_what_output
                    if virt_what_output:
                        # Writes all virt-what facts to the output as a double quoted field.
                        result += '\nVirt-what Facts, "%s"' % virt_what_output.rstrip().replace('\n', ', ')
                    else:
                        result += '\nVirt Host, None'
            else:
                result += "N"
            dmiinfo = self.run_com('dmidecode -t 4')[1].strip()
            core_count_match = re.findall('Core Count: ([0-9]+)', dmiinfo)
            socket_count = len(re.findall('Socket Designation', dmiinfo))
            num_cores = sum([int(x) for x in core_count_match])

            result += "\nCores, %i" % num_cores
            result += "\nSockets, %i" % socket_count

        self.save_results(result, host)

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

        if not self.ssh:
            print "Please submit %s.zip\n" % host

    # Ensures the command is run on the appropriate machine
    def run_com(self, com):
        if self.ssh:
            command = "ssh %s@%s '%s'" % (self.user, host, com)
            return commands.getstatusoutput(command)
        else:
            return commands.getstatusoutput(com)

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

if __name__ == '__main__':
    PackScanCli()
