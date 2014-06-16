#!/usr/bin/perl


if (!@ARGV) {
  print "Usage:  ./pack-info-ssh.pl FILENAME\n";
  print "\n\n FILENAME should be a file with \"USER HOST\" on each line\n";
  exit(1);
}


unless ( -e "./pack-scan.pl") {
   print "You are missing ./pack-scan.pl.  Please download this script and place it in the same directory as this script\n";
   exit(1);
}

$file = $ARGV[0];

open FILE, $file or die $!;
@lines = <FILE>;
close(FILE);

foreach(@lines) {
  print `./pack-scan.pl $_`; 
}
