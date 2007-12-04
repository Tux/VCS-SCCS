#!/usr/bin/env python
#
# sccs2rcs is a script to convert an existing SCCS history into an RCS
# history without losing any of the information contained therein.
#
# This tool has a complicated history for its size.  It began life as a 
# script in C-shell written by a hacker named Ken Cox in 1991.
#
# In 1993 I applied some minor fixes for newer RCS versions and it 
# shipped as part of one of Rich Morin's Prime Time Freeware releases.
#
# In 1994 Brian Berliner hacked Ken Cox's original in a slightly
# different direction than mine, adding more SCCS keyword translations
# and an improvement in dealing with branches.  At least, Brian *thinks*
# it was 1994...
#
# In 2002 I fixed it not to require the Berkeley sccs(1) front end.
# In 2003 I folded in a minor bug fix from Roger Pilkey.
# In 2007 I merged in the missing features from Brian Berliner's version
# and sent it to the GNU RCS project hoping they'd take it off my hands.
# 
# Then it started to bother me that I was casting the thing loose in a
# dying language, so I decided to port it to Python and clean it up.
# I added error checking, added the comments-file processing, added
# auto-checkout of RCS workfiles replacing SCCS ones, and removed
# no-longer-needed options. Finally I made it able to parse tag data from
# snapshots made by Emacs VC mode.
#
# Ken said:
# "This file may be copied, processed, hacked, mutilated, and
# even destroyed as long as you don't tell anyone you wrote it."
# Those were more innocent days.  This version is released under MIT terms. 
#
# Ken's things to note:
#   + It will NOT delete or alter your ./SCCS history under any circumstances.
#
#   + Run in a directory where ./SCCS exists and where you can create ./RCS
#
#   + Date, time, author, comments, branches, are all preserved.
#
#   + If a command fails somewhere in the middle, it bombs with
#     a message -- remove what it's done so far and try again.
#     (`rm -rf RCS; unget SCCS/s.*' should do the job.)
#     There is no recovery and exit is far from graceful.
#     If a particular module is hanging you up, consider
#     doing it separately; move it from the current area so that
#     the next run will have a better chance or working.
#     Also (for the brave only) you might consider hacking
#     the s-file for simpler problems:  I've successfully changed
#     the date of a delta to be in sync, then run "sccs admin -z"
#     on the thing [to regenerate its checksum].
#
# Eric's history:
#
# 1.1: I added some portability fixes and the -u option.  More importantly,
# I removed the dependencies on the BSD/SV `sccs' utility; this script
# will now work on any system that has the base SCCS/RCS tools available.
#
# 1.2: Merges in Roger Pilkey's fix for the case in which date spans 
# cross the millenium boundary.  Use GNU tac instead of tail, which can't 
# reverse large files properly.
#
# 1.3: Merges in Brian Berliner's branch hack from the other fork
# of this script, the one distributed with CVS.  That and four SCCS 
# keyword substitutions were we only thing it did that this didn't.
#
# 1.4: Python rewrite describe aboved.  Interface cleanup.  Auto-checkout
# of RCS workfiles corresponding to SCCS workfiles present when started.
# Lifting of VC mode snapshot info.  Initial-comments file.
#
# 1.5: Bug fix in comment extraction from Peter Grandcourt and Frederic
# G. Marand.
#
# Eric S. Raymond <esr@thyrsus.com>
#
# $Id: sccs2rcs 36 2007-09-14 20:04:00Z esr $

import os, sys, getopt, re, commands

# Here are the translations for SCCS % keywords to RCS-style $ keywords.
# The quotes surround the dollar signs are to fool RCS and later version-
# control systems when the script is checked in.  In the unlikely event
# that you need more keyword translations, add them to the end of this list.
# The ones this misses are %[ABCDFHLMPQRSTYZ]%; the script will issue
# warnings if it sees them after translation.
conversions = [
    ('%W%[ \t]*%G%',			"$""Id""$"),
    ('%W%[ \t]*%E%',			"$""Id""$"),
    ('%W%',				"$""Id""$"),
    ('%Z%%M%[ \t]*%I%[ \t]*%G%',	"$""SunId""$"),
    ('%Z%%M%[ \t]*%I%[ \t]*%E%',	"$""SunId""$"),
    ('%M%[ \t]*%I%[ \t]*%G%',		"$""Id""$"),
    ('%M%[ \t]*%I%[ \t]*%E%',		"$""Id""$"),
    ('%M%',				"$""RCSfile""$"),
    ('%I%',				"$""Revision""$"),
    ('%G%',				"$""Date""$"),
    ('%E%',				"$""Date""$"),
    ('%U%',				""),
    ]
conversions = map(lambda (s, t): (re.compile(s), t), conversions)

months = ("Jan","Feb","Mar","Apr","May","Jun",
          "Jul","Aug","Sep","Oct","Nov","Dec")

def writeable(f):
    return os.access(f, os.W_OK)

def sccsmaster(f):
    return os.path.join("SCCS", "s." + f)

def is_sccsmaster(f):
    return os.path.basename(f).startswith("s.")
    
def workfile(f):
    assert os.path.basename(f).startswith("s.")
    return os.path.basename(f)[2:]

def rcsfile(f):
    return os.path.join("RCS", f + ",v")

def record(msg):
    global logtext
    msg = "sccs2rcs: " + msg
    logtext += msg + "\n"

def progress(msg):
    global logtext
    msg = "sccs2rcs: " + msg
    logtext += msg + "\n"
    print msg

def do_it(command):
    global logtext
    logtext += "$ " + command + "\n"
    (st, out) = commands.getstatusoutput(command)
    logtext += out + "\n"
    return out + "\n"

def die(msg):
    print >>sys.stderr, "sccs2rcs: fatal error, ", msg
    record("error recovery begins")
    for master in os.listdir("SCCS"):
        if is_sccsmaster(master):
            do_it("unget " + master)
    print >>sys.stderr, """\
Danger!  Danger!
Incomplete history in ./RCS -- remove it.
Original unchanged history in ./SCCS.
"""
    if logtext:
        print "Log follows:"
        print logtext
        print "Log ends here."
    sys.exit(1)

def warn(msg):
    global logtext
    msg = "sccs2rcs: warning, " + msg
    logtext += msg + "\n" 
    print >>sys.stderr, msg

def do_it_or_die(command):
    global logtext
    logtext += "$ " + command + "\n"
    (st, out) = commands.getstatusoutput(command)
    logtext += out + "\n"
    if st != 0:
        die("'%s' failed" % command)
    return out + "\n"

if __name__ == '__main__':
    comments = None
    (options, arguments) = getopt.getopt(sys.argv[1:], "c:")
    for (switch, val) in options:
        if switch == '-c':
            comments = val

    # User may have supplied a comments file
    initstrings = {} 
    if comments:
        for line in open(comments):
            try:
                line = line.strip()
                if not line:	# ignore blank lines
                    continue
                (filename, initstring) = line.split(":")
            except ValueError:
                die("ill-formed line '%s' in comments file" % line)
            if filename in initstrings:
                die("duplicate filename in initstrings")
            initstrings[filename] = initstring.strip()

    # If the CSSC package is installed, the SCCS commands might be here.
    # This assumption works under Debian/Ubuntu and will be harmless elsewhere.
    os.environ["PATH"] += ":/usr/lib/cssc"

    logtext = "" 

    # Sanity checks on the directory
    if not writeable("."):
        die("./ is not writeable by you.")
    elif not os.path.isdir("SCCS"):
        die("no SCCS directory to convert.")
    for filename in os.listdir("SCCS"):
        if filename.startswith("s.") and writeable(filename):
            die(filename + " is locked for edit...unlock before converting.")
    if os.path.isdir("RCS"):
        warn("RCS directory already exists.")
        if len(os.listdir("RCS")) > 2:	# Allow . and ..
               die("RCS directory is nonempty.")
    else:
        try:
            os.mkdir("RCS")
        except OSError:
            die("failed while attempting to create RCS directory.")

    # Loop over every s-file in SCCS dir
    workfiles = []
    for master in filter(lambda f: f.startswith("s."), os.listdir("SCCS")):
        stem = master[2:]
        firsttime = True

        # These are the files we'll need to restore later
        if os.path.exists(stem):
            workfiles.append(stem)

        # Extract a list of revisions from the master 
        revisions = []
        try:
            for line in os.popen("prs " + sccsmaster(stem), "r"):
                if line.startswith("D "):
                    revisions.append(line.split()[1])
        except OSError:
            die("open of master file %s failed" % master)
        except IndexError:
            die("garbled revision line in master file " + master)
        revisions.reverse()

        # Now use prs to run through the revision list extracting data
        record("%s revisions: %s" % (stem, ", ".join(revisions)))
        for rev in revisions:
            cmd = 'prs -d":Dd: :Dm: :Dy: :T: :P:" -r%s SCCS/s.%s' % (rev, stem)
            date = do_it_or_die(cmd).strip()
            try:
                (day, month, year, tod, author) = date.split()
            except ValueError:
                die("prs output %s from '%s'was ill-formed" % (`date`, cmd))

            # We assume here that no SCCS archives were made before 1970.
            # If you're converting an SCCS archive made after 2070, you lose.
            if int(year) < 70:
                year = "20" + year
            else:
                year = "19" + year

            rcsdate = day + " " + months[int(month)-1] + " " + year + " " + tod
            progress("==> file %s, rev=%s, date=%s, author=%s" \
                  % (stem, rev, rcsdate, author)) 
            do_it_or_die("get -e -r%s %s" % (rev, sccsmaster(stem)))
            record("checked out of SCCS")

            # replace SCCS keywords with RCS keywords
            try:
                rfp = open(stem, "r")
                stemtext = rfp.read()
                rfp.close()
                for (regexp, rcskey) in conversions:
                    stemtext = regexp.sub(rcskey, stemtext)
                wfp = open(stem, "w")
                wfp.write(stemtext)
                wfp.close()
            except OSError:
                    die("keyword substitution failed")
            record("performed keyword substitutions")

            # check file into RCS
            if firsttime:
                firsttime = False
                if stem in initstrings:
                    cmd = 'ci -f -r%s -d"%s" -w%s -t-"%s" %s' \
                          % (rev, rcsdate, author, initstrings[stem], stem)
                else:
                    if initstrings:
                        warn("no description for %s in comments file" % stem)
                    cmd = 'ci -f -r%s -d"%s" -w%s -t/dev/null %s' \
                          % (rev, rcsdate, author, stem)
                cmd = "echo 'Initial revision.' | " + cmd
                do_it_or_die(cmd)
                record("initial checkin successful")
            else:
                # get RCS lock    
                revparts = rev.split(".")
                lckrev = ".".join(revparts[:-1])
                if rev.count(".") > 1:
                    # need to lock the branch -- it is OK if the lock fails
                    #
                    # I asked Brian and he explained this as follows:
                    # "As it turns out, with RCS, if you are adding the
                    # first revision of a new branch, you don't need
                    # to lock the trunk. In fact, you don't want to
                    # lock the trunk because checking in the revision
                    # on the branch will not unlock the trunk. So, the
                    # hack I applied was to get it to add branches
                    # correctly."
                    do_it("rcs -l%s %s" % (lckrev, stem))
                    record("got branch lock")
                else:
                    # need to lock the trunk -- must succeed
                    do_it_or_die("rcs -l %s" % (stem,))
                    record("got trunk lock")
                # Extract the delta message for this revision
                deltamsg = do_it_or_die("prs -r%s SCCS/s.%s" % (rev, stem))
                deltalines = deltamsg.split("\n")
                while deltalines:
                    line = deltalines[0]
                    deltalines.pop(0)
                    if line.startswith("COMMENTS"):
                        break
                # Strip ;eading blank lines if present.
                if deltalines != ['', '']:
                    while not deltalines[0].strip():
                        deltalines.pop(0)
                deltamsg = "\n".join(deltalines)
                cmd = 'ci -f -r%s -d"%s" -w%s %s' % (rev, rcsdate, author, stem)
                # FIXME: output of this command isn't logged
                record("$ " + cmd)
                try:
                    cfp = os.popen(cmd, "w")
                    cfp.write(deltamsg)
                    cfp.close()
                except OSError:
                    die("RCS checkin of delta failed")
            # We're done with this master, unlock it.
	    do_it_or_die("unget -r%s %s" % (rev, sccsmaster(stem)))

    # Generate tags from snapshots created by Emacs VC mode
    tagnames = os.path.join("SCCS", "VC-names")
    if os.path.exists(tagnames):
        for line in open(tagnames):
            try:
                (tag, dummy, filename, rev) = line.split()
            except ValueError:
                die("tags table in bad format.")
            do_it_or_die("rcs -n%s:%s %s" % (tag, rev, os.path.basename(filename)))

    # Replace all files for which there exist SCCS masters,
    progress("replacing workfiles...")
    for filename in os.listdir("SCCS"):
        if is_sccsmaster(master):
            do_it("co " + rcsfile(workfile(master)))
    progress("done.")

# sccs2rcs ends here
