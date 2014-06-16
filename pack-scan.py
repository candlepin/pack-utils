#!/usr/bin/env python
import sys
import time
import gettext
import optparse
import commands
import subprocess

_ = gettext.gettext

class PackScanCli(object):
	def __init__(self):
		self.rhcount = 0
		self.greatest = []
		self.greatest_build = []
		self.cols = []
		self.user = None
		self.host = None
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
				self.user, self.host = self.options.user_host
				print 'user: %s\nhost: %s' % (self.user, self.host)
				self.ssh = True
			except ValueError, e:
				print 'NO GOOOD'
		else:
			self.host = self.run_com('hostname')
		# if len(args) == 2:
		# 	self.user = args[1]
		# 	self.host = args[0]
		# else:
		# 	print _('No host provided. Running for localhost')
		# 	self.host = self.run_com('hostname')
		release = self.run_com('cat /etc/redhat-release')
		release = release.strip()
		self.host = self.host.strip()

		output = self.run_com('rpm -qa --qf "%{NAME}|'
			'%{VERSION}|'
			'%{RELEASE}|'
			'%{INSTALLTIME}|'
			'%{VENDOR}|'
			'%{BUILDTIME}|'
			'%{BUILDHOST}|'
			'%{SOURCERPM}|'
			'%{LICENSE}|'
			'%{PACKAGER}\n"')

		lines = output.split('\n')

		self.greatest = []
		self.greatest_build = []
		self.rhcount = 0

		for line in lines:
			self._update_rh_count(line.split("|"))

		result = ""
		curr_date = self.run_com('date +%s').strip()
		result = "%s (%s)  -  %s" % (self.host, release, curr_date)

		if (self.rhcount != 0):
			result += "\nRed Hat (Y/N), Y\n"
			result += "RH Pkgs, %s/%s" % (self.rhcount, len(lines))
			result += "\nLast Installed, "
			result += self.details_install(self.greatest)

			result += "\nLast Built, %s" % self.details_built(self.greatest_build)
		else:
			result += "\nRed Hat (Y/N), N\n"

		self.save_results(result, self.host)

	def _update_rh_count(self, col):
		if 'redhat.com' in col[6] and 'fedora' not in col[6] and 'rhndev' not in col[6]:
			self.rhcount += 1
			if len(self.greatest) == 0:
				self.greatest = col
			elif self.greatest[3] < col[3]:
				self.greatest = col
			if len(self.greatest_build) == 0:
				self.greatest_build = col
			elif self.greatest_build[5] < col[5]:
				self.greatest_build = col

	def save_results(self, output, host):
		with open('%s.csv' % host, 'w') as f:
			f.write(output)
		subprocess.call(["zip", "%s.zip" % host, "%s.csv" % host])
		subprocess.call(["rm", "%s.csv" % host])
		if not self.ssh:
			print "Please submit %s.zip\n" % host

	def run_com(self, com):
		if self.ssh:
			command = "ssh %s@%s '%s'" % (self.user, self.host, com)
			return commands.getoutput(command)
		else:
			return commands.getoutput(com)

	def details_built(self, cols):
		tmp = "%s-%s-%s" % (cols[0], cols[1], cols[2])
		local_time = time.localtime(float(cols[5]))
		tmp += " Built: %s" % time.strftime("%x %X",local_time)
		return tmp

	def details_install(self, cols):
		tmp = "%s-%s-%s" % (cols[0], cols[1], cols[2])
		local_time = time.localtime(float(cols[3]))
		tmp += " Installed: %s" % time.strftime("%x %X",local_time)
		return tmp

	def add_options(self):
		self.parser.add_option("-r", "--remote", help=_("Executes pack-scan using ssh for the given [USER HOST]"), dest="user_host", default=None, nargs=2)
		self.parser.add_option("-f", "--file", help=_("File of [USER HOST] to run the tool against."), dest="file")


if __name__ == '__main__':
	PackScanCli()
