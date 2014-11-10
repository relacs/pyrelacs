#!/usr/bin/python
import getopt
import os
import sys
from shutil import copyfile

helptxt = """
    stimuli_repair.py [OPTIONS] datadir1 [datadir2 [datadir3 [...]]]

    checks the stimuli.dat in the data directory for missing data and inserts -0 whereever data is missing.

    -h              : display help
    -o              : outputfile name (default stimuli.dat)
    -s              : dummy data to insert (default "-0")
    -n              : don't make a backup of stimuli.dat
    """

if len(sys.argv) < 2:
    print helptxt
    sys.exit(2)
try:
    opts, args = getopt.getopt(sys.argv[1:], "hs:o:n")
except:
    print helptxt
    sys.exit(2)

# set the default values
opt_dict = dict(opts)
if '-h' in opt_dict:
    print helptxt
    sys.exit(0)
outfile = opt_dict.pop('-o', 'stimuli.dat')
dummy = opt_dict.pop('-s', '-0')
dont_backup = '-n' in opt_dict

for datadir in args:
    with open(datadir + '/stimuli.dat', 'r') as fid:
        lines = fid.readlines()
        key_on = False
        for i, line in enumerate(lines):
            if line.startswith('#Key'):
                key_on = True
                continue
            if key_on:
                if line.startswith('#'):
                    continue
                elif line.strip():
                    key_on = False
                    continue
                else:
                    print "Found erroneous line in "
                    lines[i]=  dummy + '\n'
                    key_on = False
    if not dont_backup:
        copyfile(datadir + '/stimuli.dat', datadir + '/stimuli.dat~')

    with open(datadir + '/' + outfile, 'w') as fid:
        fid.write("".join(lines))