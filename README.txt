
This package includes a few utilities to help discover things about your systems:

1.  pack-list.sh    

   Prints a lot of information about the packages installed on the system it is run.  The resulting files are saved in HOSTNAME.tar.bz2.

2.  pack-list-verify.sh 

   Does the same function as pack-list.sh, but also verifies the md5sum of all files installed.  The resulting files are saved in HOSTNAME.tar.bz2

3.  pack-scan.pl

   On the system that it is run, it gathers the hostname, whether any packages built at Red Hat (non fedora) are installed, the last Red Hat package installed, and the date of the last Red Hat package installed.  This information is taken and written to a file and then zipped.

4.  pack-scan-ssh.pl

   Ssh's into a list of systems and gathers the same information as 'pack-scan.pl'.  Should be run as:

   ./pack-scan-ssh.pl filename.txt

the file should have a list of user and hosts such as:

root server1.example.com
myuser server2.example.com
joeuser webserver.example.com


Ideally you will have shared SSH keys setup so a password is not needed.  If that is not the case, ssh will prompt you for a password twice for each host.  The user does not need to be root, but simply needs shell access.

This program outputs the information into a zip file for each host.
