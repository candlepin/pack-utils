#!/bin/bash

host=`hostname`
file=$host-packages.txt
rpm -qa --qf "%{NAME}|%{VERSION}|%{RELEASE}|%{INSTALLTIME}|%{VENDOR}|%{BUILDTIME}|%{BUILDHOST}|%{SOURCERPM}|%{LICENSE}|%{PACKAGER}\n" > $file
tar -cjf $host.tar.bz2 $file
echo "please submit $host.tar.bz2"
rm $file
