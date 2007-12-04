#!/pro/bin/perl

use strict;
use warnings;

# Sccs2rcs is a script to convert an existing SCCS history into an RCS
# history without losing any of the information contained therein.
# It has been tested under the following OS's:
#     SunOS 4.1.3 5.6 5.7
#     Linux
#
# Things to note:
#   + It will NOT delete or alter your ./SCCS history under any
#     circumstances.
#
#   + Run in a directory where ./SCCS exists and where you can
#       create ./RCS
#
#   + /usr/local/bin is put in front of the default path.
#     (SCCS under Ultrix is set-uid sccs, bad bad bad, so
#     /usr/local/bin/sccs here fixes that)
#
#   + Date, time, author, comments, branches, are all preserved.
#
#   + If a command fails somewhere in the middle, it bombs with
#     a message -- remove what it's done so far and try again.
#         "rm -rf RCS; sccs unedit `sccs tell`; sccs clean"
#     There is no recovery and exit is far from graceful.
#     If a particular module is hanging you up, consider
#     doing it separately; move it from the current area so that
#     the next run will have a better chance or working.
#     Also (for the brave only) you might consider hacking
#     the s-file for simpler problems:  I've successfully changed
#     the date of a delta to be in sync, then run "sccs admin -z"
#     on the thing.
#
#   + After everything finishes, ./SCCS will be moved to ./old-SCCS.
#
# This file may be copied, processed, hacked, mutilated, and
# even destroyed as long as you don't tell anyone you wrote it.
#
# Ken Cox
# Viewlogic Systems, Inc.
# [EMAIL PROTECTED]
# ...!harvard!cg-atla!viewlog!kenstir
#
# Various hacks made by Brian Berliner before inclusion in CVS contrib area.
# Converted to perl by Michael Sterrett - [EMAIL PROTECTED]
#     Hard to tell if that should be filed under "mutilated" or "destroyed".

############################################################
# Globals
#
my $logfile = "/tmp/sccs2rcs_${$}_log";

# Could have used a hash for the keywords except we want to guarantee
# the order
my @sccs_keywords = (
    '%W%[       ]*%G%',
    '%W%[       ]*%E%',
    '%W%',
    '%Z%%M%[    ]*%I%[  ]*%G%',
    '%Z%%M%[    ]*%I%[  ]*%E%',
    '%M%[       ]*%I%[  ]*%G%',
    '%M%[       ]*%I%[  ]*%E%',
    '%M%',
    '%I%',
    '%G%',
    '%E%',
    '%U%',
    '%P%'
);
# This is used for checking if we need to do keyword substitution or not.
my $big_sccs_pattern = join('|', @sccs_keywords);

# the quotes surround the dollar signs to fool RCS when I check in this script
my @rcs_keywords = (
    '$'.'Id'.'$',
    '$'.'Id'.'$',
    '$'.'Id'.'$',
    '$'.'SunId'.'$',
    '$'.'SunId'.'$',
    '$'.'Id'.'$',
    '$'.'Id'.'$',
    '$'.'RCSfile'.'$',
    '$'.'Revision'.'$',
    '$'.'Date'.'$',
    '$'.'Date'.'$',
    '',
    '$'.'Source'.'$'
);

############################################################
# Subroutines
#
sub error_exit()
{
    print("\n\nDanger!  Danger!\n");
    print("Some command exited with a non-zero exit status.\n");
    print("Log file exists in $logfile.\n\n");
    print("Incomplete history in ./RCS -- remove it\n");
    print("Original unchanged history in ./SCCS\n");
    exit(1);
}

# This routine is used by the Schwartzian Transform in the main loop
sub by_version
{
    my $limit = ($#{$a} > $#{$b}) ? $#{$b} - 1 : $#{$a} - 1;

    for (my $c = 0; $c <= $limit; $c++) {
        my $x = ($a->[$c] <=> $b->[$c]);
        return $x if ($x);
    }
    return ($#{$a} > $#{$b}) ? 1 : -1;
}

# we'll assume the user set up the path correctly
# for the Pmax, /usr/ucb/sccs is suid sccs, what a pain
#   /usr/local/bin/sccs should override /usr/ucb/sccs there
$ENV{'PATH'} = '/usr/local/bin:' . $ENV{'PATH'};

############################################################
# Error checking
#
die("Error: ./ not writable by you.\n") unless ( -w '.' );
die("Error: ./SCCS directory not found.\n") unless ( -d 'SCCS' );
die("Error: ./old-SCCS directory found.\n") if ( -d 'old-SCCS' );
my @tell = `sccs tell`;
die("Error: sccs tell failed.\n") if ($?);
if (@tell) {
    die("Error: ", scalar(@tell), " file(s) out for edit...clean up before 
converting.\n");
}

if ( -d 'RCS' ) {
    print("Warning: RCS directory exists\n");
    opendir(RCS, 'RCS') or die("Couldn't opendir(RCS): $!\n");
    die("Error: RCS directory not empty\n") if (grep { !/^\.\.?$/o} readdir(RCS));
    closedir(RCS);
} else {
    mkdir('RCS', 0777) or die("Error: Failed to mkdir RCS: $!\n");
}

unlink($logfile);

# Sanity check in case the user added/changed things
unless (@sccs_keywords == @rcs_keywords) {
    die("\@sccs_keywords and \@rcs_keywords are mismatched\n");
}

############################################################
# Get some answers from user
#
print("\nDo you want to be prompted for a description of each\n");
print("file as it is checked in to RCS initially?\n");
print("(y=prompt for description, n=null description) [y] ?");
my $prompt_for_desc = (<> =~ /^y?$/io) ? 1 : 0;
print("\nThe default keyword substitutions are as follows and are\n");
print("applied in the order specified:\n");
for (my $c = 0; $c < @sccs_keywords; $c++) {
    print("\t$sccs_keywords[$c]\t==>\t$rcs_keywords[$c]\n");
}
print("\n");
print("Do you want to change them [n] ?");
if (<> =~ /^n?$/io) {
    print("good idea.\n");
} else {
    print("You can't always get what you want.\n");
    print("Edit this script file and change the variables:\n");
    print('    @sccs_keywords', "\n", '    @rcs_keywords', "\n");
    exit 0;
}

############################################################
# Loop over every s-file in SCCS dir
#
# match only "s." files and get rid of the "s." at the beginning of the name
opendir(SCCS, 'SCCS') or die("Couldn't opendir(SCCS): $!\n");
# match only "s." files and get rid of the "s." at the beginning of the name
for my $file (sort (grep { s/^s\.//o } readdir(SCCS))) {
    my $firsttime = 1;
    my %revisions; # hash so we're unique (was sort -u in csh so ...)
    # get all the prs info once to save calling "sccs prs" for *each* revision
    my @sccs_prs = `sccs prs $file` or die("sccs prs $file failed\n");

    # pick out just the revision lines and store the date/time and author
    # for the rev loop below
    for (grep { /^D /o } @sccs_prs) {
        @_ = split(' ', $_, 6);
        push(@{$revisions{$_[1]}}, $_[2] . ' ' . $_[3], $_[4]);
    }
    # remove the old file.  We overwrite to it later so this is non-critical
    unlink($file);

    # Schwartzian transform - see man perlfaq4
    # Sorting SCCS versions...what a pain.
    for my $rev ( map { $_->[$#{$_}] } sort by_version map { [ split(/\./o), $_ ] } 
keys(%revisions)) {
        my ($date, $author) = @{$revisions{$rev}};

        # Y2K fixup for date
        $date =~ s/^(\d\d)/$_ = ($1 + 0 < 70) ? "20$1" : "19$1"/oe or
            die("What the...?!! Bad dates found: $date\n");

        print("\n==> file $file, rev=$rev, date=$date, author=$author\n");

        # add RCS keywords in place of SCCS keywords and create the file
        open(F, ">$file") or die("Couldn't open $file for write: $!\n");
        # This could be faster if we read in the entire file, but that would
        # be bad for small-memory machines.  Better safe than sorry.
        for (`sccs get -k -p -r$rev $file 2>> $logfile`) {
            # only do the *slow* s// loop if we'll actually s// something.
            if (/$big_sccs_pattern/o) {
                study;
                # sed? we don't need no stinking sed - do keyword substitutions
                for (my $c = 0; $c < @sccs_keywords; $c++) {
                    s/$sccs_keywords[$c]/$rcs_keywords[$c]/g;
                    # If there aren't any more left, get out early.
                    !/$big_sccs_pattern/o and last;
                }
            }
            print(F);
        }
        close(F);
        error_exit if ($?); # check the return of the `sccs get...`

        # same output as the csh version for that warm fuzzy feeling
        print("checked out of SCCS\n");
        print("performed keyword substitutions\n");

        # check file into RCS
        if ($firsttime) {
            $firsttime = 0;
            unless ($prompt_for_desc) {
                print("about to do ci\n");
                open(CI, "|ci -f -r$rev -d\"$date\" -w$author -m\"Initial revision\" 
$file >> $logfile 2>&1") or die("ci failed");
                close(CI);
                error_exit if ($?);
                print("initial rev checked into RCS without description\n");
            } else {
                print("\nEnter a brief description of the file $file (end w/ 
Ctrl-D):\n");
                my @description = ();
                while (<>) {
                    push(@description, $_);
                }
                open(CI, "|ci -f -r$rev -d\"$date\" -m\"Initial revision\" -w$author 
$file >> $logfile 2>&1") or die("ci failed");
                print(CI @description) or die("description to ci failed\n");
                close(CI);
                error_exit if ($?);
                print("initial rev checked into RCS\n");
            }
        } else {
            # get RCS lock
            my $lckrev = $rev;
            $lckrev =~ s/\.\d+$//o;

            if ($lckrev =~ /\./o) {
                # need to lock the branch -- it is OK if the lock fails
                system("rcs -l$lckrev $file >> $logfile 2>&1");
            } else {
                # need to lock the trunk -- must succeed
                system("rcs -l $file >> $logfile 2>&1");
                error_exit if ($?);
            }
            print("got lock\n");
            my @old_comments = ();
            my $comments = 0;
            for (@sccs_prs) {
                # skip down to the revision we're looking for..until empty line
                next unless (/^D $rev\s/../^$/o);
                last if (/^$/o); # we found what we came for so get out early
                # once we find ^COMMENTS:, grab lines until we're done.
                $comments = 1, next if (/^COMMENTS:/o && !$comments);
                next unless ($comments);
                push(@old_comments, $_);
            }
            open(CI, "|ci -I -f -r$rev -d\"$date\" -w$author $file >> $logfile 2>&1") 
or die("ci failed\n");
            print(CI @old_comments);
            close(CI);
            print("checked into RCS\n");
        }
    }
}
closedir(SCCS);

############################################################
# Clean up
#
print("cleaning up...\n");
rename('SCCS', 'old-SCCS');
print("===================================================\n");
print("       Conversion Completed Successfully\n\n");
print("         SCCS history now in old-SCCS/\n");
print("===================================================\n");
exit(0);
