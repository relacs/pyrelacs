import getopt
import glob
from pprint import pprint
import re
import sys
import yaml
import numpy as np
from IPython import embed

from pint import UnitRegistry
import nix


from pyRELACS.DataClasses.RelacsFile import load, RelacsFile

ureg = UnitRegistry()

def get_number_and_unit(value_string):
    if value_string.endswith('%'):
        return (float(value_string.strip()[:-1]), '%')
    try:
        a = ureg.parse_expression(value_string)
    except:
        return (value_string, None)


    if type(a) == list:
        return (value_string, None)

    if isinstance( a, ( int, long , float) ):
        return (a, None)
    else:
        # a.ito_base_units()
        value = a.magnitude
        unit = "{:~}".format(a)
        unit = unit[unit.index(" "):].replace(" ","")

        if unit == 'min':
            unit = 's'
            value *= 60
        return (value, unit)




data_type_converter = {
    'float': nix.DataType.Double,
    'int': nix.DataType.Int64,
    'uint': nix.DataType.UInt64,
}


def insert_metadata(root, d):
    for k,v in d.iteritems():
        if isinstance(v, dict):
            sec = root.create_section(k, 'relacs.{0:s}'.format(k))
            insert_metadata(sec, v)
        else:
            value, unit = get_number_and_unit(str(v))

            if unit is None:
                root.create_property(k, [nix.Value(str(v))])
            else:
                p = root.create_property(k, [nix.Value(value)])
                p.unit = unit


def add_traces(relacsdir, stimuli, nix_file, block_name ):

    data_block = nix_file.create_block(block_name, 'nix.recording')

    meta, key, data = stimuli.selectall()

    traces = glob.glob(relacsdir + 'trace-*.raw')
    ret = []
    for _, name, _, data_type, index in [k for k in key[0] if 'traces' in k]:
        sample_interval, time_unit = get_number_and_unit(meta[0]['analog input traces']['sample interval%i' % (index,)])
        sample_unit = meta[0]['analog input traces']['unit%i' % (index,)]
        x = np.fromfile('%s/trace-%i.raw' % (relacsdir, index), np.float32)
        trace_data = data_block.create_data_array(name, "nix.voltage_trace", data_type_converter[data_type], x.shape)
        trace_data.unit = sample_unit
        trace_data.label = name
        trace_data.append_sampled_dimension(float(sample_interval)).unit = time_unit
        trace_data.data.write_direct(x)

        ret.append(trace_data)
    return ret

def add_info(nix_file, relacsdir, block):
    try:
        info = open(relacsdir + '/info.dat').readlines()
        info = [re.sub(r'[^\x00-\x7F]+',' ', e[1:]) for e in info]
        meta = yaml.load(''.join(info))
    except IOError:
        meta = {}
    sec = nix_file.create_section('info', "nix.metadata")
    block.metadata = sec
    insert_metadata(sec, meta)


def add_stimulus_meta(meta):
    if 'file' in meta:
        mf = RelacsFile(meta['file'])
        #meta['filemeta']
        me, _, _ = mf.selectall()
        me = me[0]
        meta['filemeta'] = me

    for k,v in meta.iteritems():
        if isinstance(v,dict):
            meta[k] = add_stimulus_meta(v)

    return meta


def add_spikes(stimuli, spikefile, spike_times, nix_file, nix_spiketimes):
    if 'stimspikes' in spikefile:
        repro = 'FileStimulus'
    elif 'samallspikes' in spikefile:
        repro = 'SAM'
    else:
        raise Exception('Cannot determine repro')

    print "Assuming RePro=%s" % (repro, )


    ureg = UnitRegistry()

    spikes = load(spikefile)
    spi_meta, spi_key, spi_data = spikes.selectall()


    for run_idx, (spi_d, spi_m) in enumerate(zip(spi_data, spi_meta)):
        print "\t%s run %i" % (repro, run_idx)

        if repro == 'FileStimulus':
            spi_m = add_stimulus_meta(spi_m)
        # match index from stimspikes with run from stimuli.dat
        stim_m, stim_k, stim_d = stimuli.subkey_select(RePro=repro, Run=spi_m['index'])

        if len(stim_m) > 1:
            raise KeyError('%s and index are not unique to identify stimuli.dat block.' % (repro, ))
        else:
            stim_k = stim_k[0]
            stim_m = stim_m[0]
            signal_column = [i for i,k in enumerate(stim_k) if k[:4] == ('stimulus', 'GlobalEField', 'signal', '-')][0]

            valid = []

            if stim_d == [[[0]]]:
                print("\t\tEmpty stimuli data! Continuing ...")
                continue

            for d in stim_d[0]:
                if not d[signal_column].startswith('FileStimulus-value'):
                    valid.append(d)
                else:
                    print("\t\tExcluding a reset trial from stimuli.dat")
            stim_d = valid


        if len(stim_d) != len(spi_d):
            print("""\t\t%s index %i has %i trials, but stimuli.dat has %i. Trial was probably aborted. Not including data.""" % (spikefile, spi_m['index'], len(spi_d), len(stim_d)))
            continue



        start_index, index = [(i, k[-1]) for i,k in enumerate(stim_k) if 'traces' in k and 'V-1' in k][0]
        sample_interval, time_unit = get_number_and_unit(stim_m['analog input traces']['sample interval%i' % (index,)])

        if repro == 'FileStimulus':
            duration = ureg.parse_expression(spi_m['duration']).to(time_unit).magnitude
        elif repro == 'SAM':
            duration = ureg.parse_expression(spi_m['Settings']['Stimulus']['duration']).to(time_unit).magnitude

        start_times = []

        start_indices = [d[start_index] for d in stim_d]
        for begin_index, trial in zip(start_indices, spi_d):
            start_time = begin_index*sample_interval
            start_times.append(start_time)
            spike_times.append(trial+start_time)


        start_times = np.asarray(start_times)
        durations = duration * np.ones(len(stim_d))


        tag_name = "%s-run-%i" % (repro, run_idx)
        positions = recording_block.create_data_array(tag_name+'_starts','nix.event.position', nix.DataType.Double, start_times.shape)
        positions.data.write_direct(start_times)
        positions.append_set_dimension()

        extents = recording_block.create_data_array(tag_name+'_extents','nix.event.extents', nix.DataType.Double, durations.shape)
        extents.data.write_direct(durations)
        extents.append_set_dimension()

        tag = recording_block.create_multi_tag(tag_name, 'nix.experiment_run', positions)
        tag.extents = extents
        tag.references.append(nix_spiketimes)


        for nt in nix_traces:
            tag.references.append(nt)

        sec = nix_file.create_section(tag_name, "nix.metadata")
        tag.metadata = sec

        insert_metadata(sec, stim_m)
        insert_metadata(sec, spi_m)


def add_ficurve(fifile, nix_file):
    fi = load(fifile)

    for i, (fi_meta, fi_key, fi_data) in enumerate(zip(*fi.selectall())):
        secname = 'FI-Curve-%i' % (i, )
        block = nix_file.create_block(secname, 'nix.analysis')
        fi_data = np.asarray(fi_data).T
        for (name, unit), dat in zip(fi_key, fi_data):
            if unit == 'HZ': unit = 'Hz' # fix bug in relacs

            fi_curve_data = block.create_data_array(name, "nix.trace", nix.DataType.Double, dat.shape)
            if unit != '1':
                fi_curve_data.unit = unit
            fi_curve_data.label = name
            fi_curve_data.data[:] = dat
            fi_curve_data = None

        sec = nix_file.create_section(secname, "nix.metadata")
        block.metadata = sec
        insert_metadata(sec, fi_meta)
        block = None

if __name__=="__main__":
    #--------------------------------------------------------------------------------------------
    helptxt = """
    phase_lock.py [OPTIONS] relacsdir outfile

    -h              : display help
    """

    if len(sys.argv) < 2:
        print helptxt
        sys.exit(3)
    try:
        opts, args = getopt.getopt(sys.argv[1:], "h")
    except:
        print helptxt
        sys.exit(2)

    # overwrite with parameters
    for opt, arg in opts:
        if opt == '-h':
            print helptxt
            sys.exit()

    relacsdir, nix_filename = args
    if relacsdir[-1] != '/':
        relacsdir += '/'


    nix_file = nix.File.open(nix_filename, nix.FileMode.Overwrite)
    stimuli = load(relacsdir + 'stimuli.dat')
    spike_times = []
    recordings_block_name = [e.strip() for e in relacsdir.split('/') if e][-1]


    #------------ add traces -------------------

    nix_traces = add_traces(relacsdir, stimuli, nix_file, recordings_block_name)
    recording_block = [k for k in nix_file.blocks if k.name == recordings_block_name][0]

    add_info(nix_file, relacsdir, recording_block)

    nix_spiketimes = recording_block.create_data_array('spikes', 'nix.event.spiketimes', nix.DataType.Double, (0,0))
    nix_spiketimes.append_set_dimension()

    #------------ add fi curves-------------------
    for fifile in glob.glob(relacsdir + 'ficurves*.dat'):
        add_ficurve(fifile, nix_file)
    #------------ add filestimulus -------------------
    for spikefile in glob.glob(relacsdir + 'stimspikes*.dat'):
        add_spikes(stimuli, spikefile, spike_times, nix_file, nix_spiketimes)

    for spikefile in glob.glob(relacsdir + 'samallspikes*.dat'):
        add_spikes(stimuli, spikefile, spike_times, nix_file, nix_spiketimes)


    if len(spike_times) > 0:
        spike_times = np.hstack(spike_times)
        print "storing %i spikes" % (len(spike_times),)
        spike_times.sort()
        nix_spiketimes.data_extent = (1,) + spike_times.shape # this is not how it's ought to be
        nix_spiketimes.data.write_direct(spike_times)

    nix_file.close()