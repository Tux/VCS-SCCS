#!/usr/bin/perl

# Copyright PROCURA B.V. (c) 2007-2008 H.Merijn Brand

require 5.006;

use ExtUtils::MakeMaker;

my %wm = (
    NAME	  =>   "VCS::SCCS",
    DISTNAME	  =>   "VCS-SCCS",
    AUTHOR        =>   "H.Merijn Brand <h.m.brand\@xs4all.nl>",
    VERSION_FROM  =>   "SCCS.pm",
    ABSTRACT_FROM =>   "SCCS.pm",
    PREREQ_PM     => { "Test::More" => 0,
		       "Carp"       => 0,
		       "File::Spec" => 0,
		       "POSIX"      => 0,
		       },
    dist	  => { DIST_DEFAULT => "tgzdist" }, # I hate .tar.gz
    );
$ExtUtils::MakeMaker::VERSION > 6.30 and $wm{LICENSE} = "perl";

my $rv = WriteMakefile (%wm);

1;

package MY;

sub postamble
{
    join "\n" =>
	'cover test_cover:',
	'	cover -delete',
	'	HARNESS_PERL_SWITCHES=-MDevel::Cover $(MAKE) test',
	'	cover',
	'',
	'tgzdist:	$(DISTVNAME).tar.gz',
	'	-@mv -f $(DISTVNAME).tar.gz $(DISTVNAME).tgz',
	'';
    } # postamble
