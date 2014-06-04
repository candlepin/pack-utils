#!/bin/bash

host=`hostname`
file=$host-packages.txt
rpm -qa --qf "%{NAME}|%{VERSION}|%{RELEASE}|%{INSTALLTIME}|%{VENDOR}|%{BUILDTIME}|%{BUILDHOST}|%{SOURCERPM}|%{LICENSE}|%{PACKAGER}\n" > $file
file2=$host-verify.txt
rpm -Va > $file2

tar -cjf $host.tar.bz2 $file $file2
echo "please submit $host.tar.bz2"
rm $file
rm $file2
