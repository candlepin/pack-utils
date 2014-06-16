#!/usr/bin/perl

use POSIX;


if (not @ARGV || @ARGV != 2) {
    print "Usage: ./pack-info.pl [USER HOST]\n";
    print "$ARGV[0]\n";
    exit(1);
}

if (@ARGV == 2) {
  our $ssh = 1;
  $host = $ARGV[1];
  $user = $ARGV[0];
}
if (not @ARGV) {
  our $ssh = 0;
  $host=`hostname`;

}


$release =&run_com('cat /etc/redhat-release');
chomp($release);
chomp($host);
$output = &run_com('rpm -qa --qf "%{NAME}|%{VERSION}|%{RELEASE}|%{INSTALLTIME}|%{VENDOR}|%{BUILDTIME}|%{BUILDHOST}|%{SOURCERPM}|%{LICENSE}|%{PACKAGER}\n"');

@lines = split(/\n/, $output);


@greatest = []; #install time
@greatest_build = [];
$rhcount = 0;


for($i = 0; $i < @lines; $i++) {
   @cols = split(/\|/, $lines[$i]);
   if (index($cols[6], 'redhat.com') > -1 and 
            index($cols[6], 'fedora') == -1 and 
            index($cols[6], 'rhndev') == -1) {
      $rhcount++;

      if ($greatest == -1) {
         @greatest = @cols;
      }
      elsif( $greatest[3] < $cols[3]) {
         @greatest = @cols;
      }
      if ($greatest_build == -1) {
         @greatest_build = @cols;
      }
      elsif( $greatest_build[5] < $cols[5]) {
         @greatest_build = @cols;
      }
   }
}




$result = "";
$curr_date = `date +%s`;
chomp($curr_date);
$result = "$host ($release)  -  ".$curr_date;

if ($rhcount != 0) {
  $result = $result."\nRed Hat (Y/N): Y\n";
  $result = $result."RH Pkgs: $rhcount/".scalar @lines;
  $result = $result."\nLast Installed: ";
  $result = $result.details_install(@greatest);

  $result = $result."\nLast Built: ";
  $result = $result.details_built(@greatest_build);
} 
else {
   $result = $result."\nRed Hat (Y/N): N\n";
}

save_results($result, $host);
exit;

sub details_install {
  @cols = @_;
  $tmp = $cols[0]."-".$cols[1]."-".$cols[2];
  $tmp = $tmp."  Installed: ";
  $time = localtime($cols[3] + 0);
  $tmp = $tmp."$time";
  return $tmp;
}

sub details_built {
  @cols = @_;
  $tmp = $cols[0]."-".$cols[1]."-".$cols[2];
  $time_build = localtime($cols[5] + 0);
  $tmp = $tmp."  Built: ".$time_build;
  return $tmp;
}


sub save_results {
   $output = $_[0];
   $host = $_[1];
   open FILE, ">>", "$host.txt" or print "ERROR, cannot write file";
   print FILE $output;
   close FILE;
   `zip $host.zip $host.txt`;
   `rm $host.txt`;
   if(!$ssm) {
      print "Please submit $host.zip\n";
   }
}

sub run_com {
   $com = $_[0];
   if ($ssh) {
      $com = "ssh ".$user."@".$host." '".$com."'";
      return `$com`;
   }
   else {
      return `$com`;
   }
}
