#!/usr/bin/env python
import sys
import time
import optparse
import commands
import subprocess
import re

class PackScanCli(object):
    def __init__(self):
        self.options = None
        self.args = None
        self.parser = optparse.OptionParser()
        self.add_options()

    def main(self, args=None):

        if not args:
            args = sys.argv[1:]

        self.options, self.args = self.parser.parse_args(args)
        if self.options.filename:
            PackScanFileCmd(self.options.filename).main()
        elif hasattr(self.options, "user_host") and self.options.user_host:
            try:
                user, host = self.options.user_host
            except ValueError, e:
                print 'Invalid input. Please try again.'
                exit(1)
            PackScanCmd(user, host).main()
        else:
            PackScanCmd().main()


    def add_options(self):
        self.parser.add_option("-r", "--remote", 
            help="Executes pack-scan using ssh for the given [USER HOST]",
            dest="user_host",
            default=None,nargs=2)
        self.parser.add_option("-f", "--file", 
            help="File of [USER HOST] to run the tool against.",
            dest="filename",
            default=None)


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

class Report(object):
    def __init__(self, cmd_runner, seperator=", "):
        self.fields = [
            SimpleCommand('date'),
            SimpleCommand('hostname'),
            SimpleCommand('cat /etc/redhat-release', header="release"),
            RpmCommand(),
            VirtWhatCommand(),
            DmiDecodeCommand(),
        ]
        self.seperator = seperator
        self.cmd_runner = cmd_runner

    def row(self):
        return self.seperator.join([x.run(self.cmd_runner.run) for x in self.fields])

    def __str__(self):
        return self.row()

    def header(self):
        return self.seperator.join([x.header() for x in self.fields])

    def header_and_row(self):
        return {header: row for header, row in zip(self.header().split(", "), self.row().spilt(", "))}

class CmdRunner(object):

    def run(self, cmd):
        return commands.getstatusoutput(cmd)

class SshCmdRunner(CmdRunner):

    def __init__(self, user, host):
        self.user = user
        self.host = host

    def run(self, cmd):
        return super(CmdRunner, self).run("ssh %s@%s '%s'" % (self.user, self.host, cmd))

class Command(object):

    def __init__(self):
        self.output = None
        self.exitcode = None

    # returns the fields in csv it will return
    def header(self):
        raise NotImplementedError

    # run takes in a function cmd_runner that returns (exitcode, output) of the command it is passed
    def run(self, cmd_runner):
        result = cmd_runner.run(self.cmd)
        try:
            self.exitcode, self.output = result
            self.exitcode = int(self.exitcode)
        except ValueError:
            # assumes the cmd_runner provided returns only the output of a command
            self.output = result

        self.output = self.output.strip()
        return self.parse_output()

    def parse_output(self):
        raise NotImplementedError

class SimpleCommand(Command):
    def __init__(self, cmd, header=None):
        super(Command, self).__init__()
        self.cmd = cmd
        self._header = header or self.cmd
        

    def header(self):
        return self._header

    def parse_output(self):
        return self.output

class RpmCommand(Command):

    def __init__(self):
        super(Command, self).__init__()
        self.cmd = 'rpm -qa --qf "%{NAME}|%{VERSION}|%{RELEASE}|%{INSTALLTIME}|%{VENDOR}|%{BUILDTIME}|%{BUILDHOST}|%{SOURCERPM}|%{LICENSE}|%{PACKAGER}\n"'
        self._header = "Red Hat (Y/N), RH Pkgs, Last Installed, Last Built"

    def header(self):
        return self._header

    def parse_output(self):
        # We need to skip the parsing of the output of rpm if it exited with non-zero exitcode
        # if int(self.exitcode) != 0:
        #     return ", ".join(["rpm exited with nonzero exitcode"]*4)
        installed_packages = [PkgInfo(line) for line in self.output.splitlines()]
        rh_packages = filter(PkgInfo.is_red_hat_pkg, installed_packages)
        last_installed = max(rh_packages, key= lambda x: x.install_time)
        last_built = max(rh_packages, key= lambda x: x.build_time)
        is_red_hat = "Y" if len(rh_packages) > 0 else "N"
        rhpkgs = "%s/%s" % (len(rh_packages), len(installed_packages))
        return ", ".join([is_red_hat, rhpkgs, last_installed.details_install(), last_built.details_built()])

class VirtWhatCommand(Command):
    
    def __init__(self):
        super(Command, self).__init__()
        self.cmd = 'virt-what'
        self._header = "virt-what"

    def header(self):
        return self._header

    def parse_output(self):
        if self.output or self.output != "":
            if self.exitcode != 0:
                return '"%s"' % self.output.replace('\n', ',')
            else:
                return self.output
        else:
            return "Baremetal"

class DmiDecodeCommand(Command):

    def __init__(self):
        super(Command, self).__init__()
        self.cmd = 'dmidecode -t 4'
        self._header = 'sockets, cores'

    def header(self):
        return self._header

    def parse_output(self):
        if self.exitcode != 0:
            return ", ".join(["dmiinfo exited with nonzero exitcode"]*2)
        else:
            sockets = len(re.findall('Socket Designation', self.output))
            core_count_match = re.findall('Core Count: ([0-9]+)', self.output)
            cores = sum([int(x) for x in core_count_match]) 
            return ", ".join([str(sockets), str(cores)])

class PackScanCmd(object):
    name = "base"
    def __init__(self, user=None, host=None):
        self.user = user
        self.host = host

    def main(self):
        results = Report(SshCmdRunner(self.user, self.host)) if self.user and self.host else \
        Report(CmdRunner())
        PackScanCmd.save_results(results)

    @staticmethod
    def save_results(report):
        row = report.row()
        host = row.split(", ")[1]
        filename = '%s.csv' % host
        try:
            f = open(filename, 'w')
            f.write(report.row())
            f.close()
        except EnvironmentError, e:
            sys.stderr.write('Error writing to %s: %s\n' % (filename, e))
            f.close()

class PackScanFileCmd(object):
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

if __name__ == '__main__':
    PackScanCli().main()
