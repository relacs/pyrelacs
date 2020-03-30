import re
from .RelacsFile import SpikeFile, BeatFile, StimuliFile, FICurveFile, RelacsFile, TraceFile, read_info_file


def load(filename):
    if re.match(".*info.*\.dat$", filename):
        return read_info_file(filename)
    elif re.match(".*stimspikes.*\.dat$", filename) or re.match(".*samallspikes.*\.dat$", filename):
        return SpikeFile(filename)
    elif re.match(".*ficurve-spikes.*\.dat$", filename) or re.match(".*stimulus-whitenoise-spikes.*\.dat$", filename) \
            or re.match(".*saveevents.*\.dat$", filename) or re.match(".*basespikes.*\.dat$", filename):
        return SpikeFile(filename, mergetrials=False)
    elif re.match(".*beats-eod.*\.dat$", filename):
        return BeatFile(filename)
    elif re.match(".*stimuli.*\.dat$", filename):
        return StimuliFile(filename)
    elif re.match(".*ficurves.*\.dat$", filename):
        return FICurveFile(filename)
    elif re.match(".*ficurve-.*\.dat$", filename) or re.match(".*vicurve-.*\.dat$", filename) \
            or re.match(".*transferfunction-data.*\.dat$", filename) \
            or re.match(".*stimulus-whitenoise-trace.*\.dat$", filename) \
            or re.match(".*membraneresistance-trace.*\.dat$", filename) \
            or re.match(".*membraneresistance-expfit.*\.dat$", filename) \
            or re.match(".*Whitenoise.*\.dat$", filename) \
            or re.match(".*baserate.*\.dat$", filename) \
            or re.match(".*baseisih.*\.dat$", filename):
        return TraceFile(filename)
    else:
        return RelacsFile(filename)
