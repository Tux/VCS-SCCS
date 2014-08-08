#!/pro/bin/perl

use 5.014;
use warnings;
use Time::Local;

my %tzoffset;
my $tzoffset = sub {
    use integer;
    my $offset_s = timegm (localtime ($_[0])) - $_[0];
    my $off = abs $offset_s / 60;
    my ($off_h, $off_m) = ($off / 60, $off % 60);
    $tzoffset{$offset_s} ||= ( $offset_s >= 0 ? "+" : "-" )
	. sprintf "%02d%02d", $off_h, $off_m;
    };

say $tzoffset->(time);
