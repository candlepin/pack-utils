#!/usr/bin/env python
import subprocess
import sys
import time
import csv
import gettext

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
		self.main()

	def main(self):
		#TODO: Add arg parsing for list of hosts to cover functionality of pack-scan-ssh.pl
		# p = argparse.ArgumentParser(description=_("Gathers basic information on Red Hat packages\ninstalled on the system."))
		args = sys.argv[1:]
		if len(args) == 1 or len(args) > 2:
			print "Usage: ./pack-info.pl [USER HOST]\n"
			sys.exit(1)

		if len(args) == 2:
			self.user = args[1]
			self.host = args[0]
		else:
			print _('No host provided. Running for localhost')
			self.host = self.run_com('hostname')
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

		self.cols = [x.split('|') for x in lines]
		[self._update_rh_count(col) for col in self.cols]

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
		if ('redhat.com' in col and 
	       'fedora' not in col and 
	       'rhndev' not in col):
			self.rhcount += 1

	      	if (len(self.greatest) == 0):
	        	self.greatest = col
	      	elif self.greatest[3] < self.cols[3]:
	        	self.greatest = col

	      	if (len(self.greatest_build) == 0):
	        	self.greatest_build = col

	        elif (self.greatest_build[5] < self.cols[5]):
	        	self.greatest_build = col

	def save_results(self, output, host):
		with open('%s.csv' % host, 'w') as f:
			f.write(output)
		subprocess.call(["zip", "%s.zip" % host, "%s.csv" % host])
		subprocess.call(["rm", "%s.csv" % host])
		if not ssh:
			print "Please submit $host.zip\n"

	def run_com(self, com, ssh=False, **keywords):
		if self.ssh:
			com = ["ssh", "%s@'%s'" % (user, host), str(com)]
			return subprocess.check_output(com)
		else:
			return subprocess.check_output(com.split(' '))

	def details_built(self, cols):
		tmp = "%s-%s-%s" % (cols[0], cols[1], cols[2])
		tmp += " Installed: "
		time = time.localtime(cols[5] + 0)
		tmp += str(time)
		return tmp

	def details_install(self, cols):
		tmp = "%s-%s-%s" % (cols[0], cols[1], cols[2])
		tmp += " Installed: "
		time = time.localtime(cols[3] + 0)
		tmp += str(time)
		return tmp

if __name__ == '__main__':
	PackScanCli()