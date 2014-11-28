import re
from .RelacsFile import SpikeFile, BeatFile, StimuliFile, FICurveFile, RelacsFile


def load(filename):
    if re.match(".*stimspikes.*\.dat$", filename):
        return SpikeFile(filename)
    elif re.match(".*samallspikes.*\.dat$", filename):
         return SpikeFile(filename)
    elif re.match(".*beats-eod.*\.dat$", filename):
         return BeatFile(filename)
    elif re.match(".*stimuli.*\.dat$", filename):
        return StimuliFile(filename)
    elif re.match(".*ficurves.*\.dat$", filename):
        return FICurveFile(filename)
    else:
        return RelacsFile(filename)
