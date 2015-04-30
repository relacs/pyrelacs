import re
from .RelacsFile import SpikeFile, BeatFile, StimuliFile, FICurveFile, RelacsFile, TraceFile

#
def load(filename):
    if re.match(".*stimspikes.*\.dat$", filename) or re.match(".*samallspikes.*\.dat$", filename):
        return SpikeFile(filename)
    elif re.match("ficurve-spikes.*\.dat$", filename):
         return SpikeFile(filename, mergetrials=False)
    elif re.match(".*beats-eod.*\.dat$", filename):
         return BeatFile(filename)
    elif re.match(".*stimuli.*\.dat$", filename):
        return StimuliFile(filename)
    elif re.match(".*ficurves.*\.dat$", filename):
        return FICurveFile(filename)
    elif re.match(".*ficurve-.*\.dat$", filename) or re.match(".*vicurve-.*\.dat$", filename) \
            or re.match(".*transferfunction-data.*\.dat$", filename):
        return TraceFile(filename)
    else:
        return RelacsFile(filename)
