from os import path
try:
    from itertools import izip
except:
    izip = zip
import types
from numpy import array, arange, NaN, fromfile, float32, asarray, unique, squeeze, Inf, isnan, fromstring
from numpy.core.records import fromarrays
#import nixio as nix
import re
import warnings
import gzip

identifiers = {
    'stimspikes1.dat': lambda info: ('RePro' in info[-1] and info[-1]['RePro'] == 'FileStimulus'),
    'samallspikes1.dat': lambda info: ('RePro' in info[-1] and info[-1]['RePro'] == 'SAM'),
}


def isfloat(value):
    try:
        float(value)
        return True
    except ValueError:
        return False


def info_filter(iter, filterfunc):
    for info, key, dat in iter:
        if filterfunc(info):
            yield info, key, dat

def iload_io_pairs(basedir, spikefile, traces, filterfunc=None):
    """
    Iterator that returns blocks of spike traces and spike times from the base directory basedir (e.g. 2014-06-06-aa)
    and the spiketime file (e.g. stimspikes1.dat). A filter function can filter out unwanted blocks. It gets the info
    (see iload and iload trace_trials) from all traces and spike times and has to return True is the block is wanted
     and False otherwise.

     :param basedir: basis directory of the recordings (e.g. 2014-06-06-aa)
     :param spikefile: spikefile (e.g. stimspikes1.dat)
     :param traces: trace numbers as a list (e.g. [1,2])
     :param filterfunc: function that gets the infos from all traces and spike times and indicates whether the block is wanted or not
    """

    if filterfunc is None: filterfunc = lambda inp: True

    if type(traces) is not types.ListType:
        traces = [traces]

    assert spikefile in identifiers, """iload_io_pairs does not know how to identify trials in stimuli.dat which
                                        correspond to trials in {0}. Please update pyRELACS.DataLoader.identifiers
                                        accordingly""".format(spikefile)
    iterators = [info_filter(iload_trace_trials(basedir, tn), identifiers[spikefile]) for tn in traces] \
                + [iload_spike_blocks(basedir + '/' + spikefile)]

    for stuff in izip(*iterators):
        info, key, dat = zip(*stuff)
        if filterfunc(*info):
            yield info, key, dat

def iload_spike_blocks(filename):
    """
    Loades spike times from filename and merges trials with incremental trial numbers into one block.
    Spike times are assumed to be in seconds and are converted into ms.
    """
    current_trial = -1
    ret_dat = []
    old_info = old_key = None
    for info, key, dat in iload(filename):
        if 'trial' in info[-1]:
            if int(info[-1]['trial']) != current_trial + 1:
                yield old_info[:-1], key, ret_dat
                ret_dat = []

            current_trial = int(info[-1]['trial'])
            if not any(isnan(dat)):
                ret_dat.append(squeeze(dat)/1000.)
            else:
                ret_dat.append(array([]))
            old_info, old_key = info, key

        else:
            if len(ret_dat) > 0:
                yield old_info[:-1], old_key, ret_dat
                ret_dat = []
            yield info, key, dat
    else:
        if len(ret_dat) > 0:
            yield old_info[:-1], old_key, ret_dat





def iload_trace_trials(basedir, trace_no=1, before=0.0, after=0.0 ):
    """
    returns:
    info : metadata from stimuli.dat
    key : key from stimuli.dat
    data : the data of the specified trace of all trials
    """
    x = fromfile('%s/trace-%i.raw' % (basedir, trace_no), float32)
    p = re.compile('([-+]?\d*\.\d+|\d+)\s*(\w+)')

    for info, key, dat in iload('%s/stimuli.dat' % (basedir,)):
        X = []
        val, unit = p.match(info[-1]['duration']).groups()
        val = float( val )
        if unit == 'ms' :
            val *= 0.001
        duration_index = key[2].index('duration')

        sval, sunit = p.match(info[0]['sample interval%i' % trace_no]).groups()
        sval = float( sval )
        if sunit == 'ms' :
            sval *= 0.001

        l = int(before / sval)
        r = int((val+after) / sval)

        if dat.shape == (1,1) and dat[0,0] == 0:
            warnings.warn("iload_trace_trials: Encountered incomplete '-0' trial.")
            yield info, key, array([])
            continue


        for col, duration in zip(asarray([e[trace_no - 1] for e in dat], dtype=int), asarray([e[duration_index] for e in dat], dtype=float32)):  #dat[:,trace_no-1].astype(int):
            tmp = x[col-l:col + r]

            if duration < 0.001: # if the duration is less than 1ms
                warnings.warn("iload_trace_trials: Skipping one trial because its duration is <1ms and therefore it is probably rubbish")
                continue

            if len(X) > 0 and len(tmp) != len(X[0]):
                warnings.warn("iload_trace_trials: Setting one trial to NaN because it appears to be incomplete!")
                X.append(NaN*X[0])
            else:
                X.append(tmp)

        yield info, key, asarray(X)


def iload_traces(basedir, repro='', before=0.0, after=0.0 ):
    """
    returns:
    info : metadata from stimuli.dat
    key : key from stimuli.dat
    time : an array for the time axis
    data : the data of all traces of a single trial 
    """
    p = re.compile('([-+]?\d*\.\d+|\d+)\s*(\w+)')
    reproid = 'RePro'
    deltat = None

    # open traces files:
    sf = []
    for trace in range(1, 1000000) :
        if path.isfile( '%s/trace-%i.raw' % (basedir, trace) ) :
            sf.append( open( '%s/trace-%i.raw' % (basedir, trace), 'rb' ) )
        else :
            break

    basecols = None

    for info, key, dat in iload('%s/stimuli.dat' % (basedir,)):
        if deltat is None:
            deltat, tunit = p.match(info[0]['sample interval%i' % 1]).groups()
            deltat = float( deltat )
            if tunit == 'ms' :
                deltat *= 0.001
                
        if 'repro' in info[-1] or 'RePro' in info[-1]:
            if not reproid in info[-1]:
                reproid = 'repro'
            if len(repro) > 0 and repro != info[-1][reproid] and \
               basecols is None:
                continue
            baserp = (info[-1][reproid] == 'BaselineActivity')
            duration_indices = [i for i, x in enumerate(key[2]) if x == "duration"]
        else:
            baserp = True
            duration_indices = []

        if dat.shape == (1,1) and dat[0,0] == 0:
            warnings.warn("iload_traces: Encountered incomplete '-0' trial.")
            yield info, key, array([])
            continue
        
        if baserp:
            basecols = []
            basekey = key
            baseinfo = info
        for d in dat :
            if not baserp and not basecols is None:
                x = []
                xl = []
                for trace in range(len(sf)) :
                    col = int(d[trace])
                    sf[trace].seek( basecols[trace]*4 )
                    buffer = sf[trace].read( (col - basecols[trace])*4 )
                    tmp = fromstring(buffer, float32)
                    x.append(tmp)
                    xl.append(len(tmp))
                ml = min(xl)
                for k in range(len(x)):
                    if len(x[k]) > ml:
                        warnings.warn("trunkated trace %d to %d" % (k, ml))
                        x[k] = x[k][:ml]
                xtime = arange( 0.0, len(x[0]))*deltat - before
                yield baseinfo, basekey, xtime, asarray( x )
                basecols = None
                if len(repro) > 0 and repro != info[-1][reproid]:
                    break

            if len(duration_indices) > 0:
                duration = max([d[i] for i in duration_indices if not isnan(d[i])])
                if duration < 0.001: # if the duration is less than 1ms
                    warnings.warn("iload_traces: Skipping one trial because its duration is <1ms and therefore it is probably rubbish")
                    continue
                l = int(before / deltat)
                r = int((duration+after) / deltat)
            x = []
            xl = []
            for trace in range(len(sf)) :
                col = int(d[trace])
                if baserp:
                    if col < 0:
                        col = 0
                    basecols.append(col)
                    continue
                sf[trace].seek( (col-l)*4 )
                buffer = sf[trace].read( (l+r)*4 )
                tmp = fromstring(buffer, float32)
                x.append(tmp)
                xl.append(len(tmp))
            if baserp:
                break
            ml = min(xl)
            for k in range(len(x)):
                if len(x[k]) > ml:
                    warnings.warn("trunkated trace %d to %d" % (k, ml))
                    x[k] = x[k][:ml]
            time = arange( 0.0, len(x[0]) )*deltat - before
            yield info, key, time, asarray( x )
            
    for trace in range(len(sf)) :
        sf[trace].close()


def iload(filename):
    meta_data = []
    new_meta_data = []
    key = []

    within_key = within_meta_block = within_data_block = False
    currkey = None
    data = []

    with open_any(filename, 'rt') as fid:
        for line in fid:

            line = line.rstrip().lstrip()

            if within_data_block and (line.startswith('#') or not line):
                within_data_block = False

                yield list(meta_data), tuple(key), array(data)
                data = []

            # Key parsing
            if line.startswith('#Key'):
                key = []
                within_key = True
                continue
            if within_key:
                if not line.startswith('#'):
                    within_key = False
                else:

                    key.append(tuple([e.strip() for e in line[1:].split("  ") if len(e.strip()) > 0]))
                    continue

            # fast forward to first data point or meta data
            if not line:
                within_key = within_meta_block = False
                currkey = None
                continue
            # meta data blocks
            elif line.startswith('#'): # cannot be a key anymore
                if not within_meta_block:
                    within_meta_block = True
                    new_meta_data.append({})

                if ':' in line:
                    tmp = [e.rstrip().lstrip() for e in line[1:].split(':')]
                elif '=' in line:
                    tmp = [e.rstrip().lstrip() for e in line[1:].split('=')]
                else:
                    currkey = line[1:].rstrip().lstrip()
                    new_meta_data[-1][currkey] = {}
                    continue

                if currkey is None:
                    new_meta_data[-1][tmp[0]] = tmp[1]
                else:
                    new_meta_data[-1][currkey][tmp[0]] = tmp[1]

            else:

                if not within_data_block:
                    within_data_block = True
                    n = len(new_meta_data)
                    meta_data[-n:] = new_meta_data
                    new_meta_data = []
                    currkey = None
                    within_key = within_meta_block = False
                data.append([float(e) if (e != '-0' and isfloat(e)) else NaN for e in line.split()])
        else:  # if for loop is finished, return the data we have so far
            if within_data_block and len(data) > 0:
                yield list(meta_data), tuple(key), array(data)


def recload(filename):
    for meta, key, dat in iload(filename):
        yield meta, fromarrays(dat.T, names=key[0])


def load(filename):
    """
    
    Loads a data file saved by relacs. Returns a tuple of dictionaries
    containing the data and the header information
    
    :param filename: Filename of the data file.
    :type filename: string
    :returns:  a tuple of dictionaries containing the head information and the data.
    :rtype: tuple

    """
    with open_any(filename, 'rt') as fid:
        L = [l.lstrip().rstrip() for l in fid.readlines()]

    ret = []
    dat = {}
    X = []
    keyon = False
    currkey = None
    for l in L:
        # if empty line and we have data recorded
        if (not l or l.startswith('#')) and len(X) > 0:
            keyon = False
            currkey = None
            dat['data'] = array(X)
            ret.append(dat)
            X = []
            dat = {}

        if '---' in l:
            continue
        if l.startswith('#'):
            if ":" in l:
                tmp = [e.rstrip().lstrip() for e in l[1:].split(':')]
                if currkey is None:
                    dat[tmp[0]] = tmp[1]
                else:
                    dat[currkey][tmp[0]] = tmp[1]
            elif "=" in l:
                tmp = [e.rstrip().lstrip() for e in l[1:].split('=')]
                if currkey is None:
                    dat[tmp[0]] = tmp[1]
                else:
                    dat[currkey][tmp[0]] = tmp[1]
            elif l[1:].lower().startswith('key'):
                dat['key'] = []

                keyon = True
            elif keyon:

                dat['key'].append(tuple([e.lstrip().rstrip() for e in l[1:].split()]))
            else:
                currkey = l[1:].rstrip().lstrip()
                dat[currkey] = {}

        elif l:  # if l != ''
            keyon = False
            currkey = None
            X.append([float(e) for e in l.split()])

    if len(X) > 0:
        dat['data'] = array(X)
    else:
        dat['data'] = []
    ret.append(dat)

    return tuple(ret)
            
            

def open_any(filename, mode = 'rt'):
    '''allows opening of .gz compressed files in addition
    to .dat files.
    
    :param filename: Filename of the data file.
    :param mode: mode in which the file will be opened. default: read-only,text-mode (important for .gz)
    :type filename: string
    :returns:  a file containing the data to be read
    :rtype: file
    '''
    
    if filename.endswith(".gz"):
        return gzip.open(filename, mode)
    else:
        return open(filename, mode)


