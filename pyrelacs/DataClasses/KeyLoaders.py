import linecache
from pprint import pprint
import types
from IPython import embed
import numpy as np

def get_positions(line, elements):
    pos = []

    for elem in elements:
        if len(pos) > 0:
            pos.append(line.find(elem, pos[-1] + 1))
        else:
            pos.append(line.find(elem))
    return pos

def position_equalizer(*args):
    amax = np.argmax([len(a) for a in args])
    retidx = len(args)*[0]

    for e in args[amax]:
        for i, idx in enumerate(retidx):
            if len(args[i]) > idx +1 and args[i][idx+1] <= e:
                retidx[i] += 1
        yield tuple([i for i in retidx])



def parse_stimuli_key(block, file):
    lines = [linecache.getline(file, i + 1) for i in range(block.start+1, block.end)]
    idx = [int(i) for i in lines[4][1:].split('  ') if i]
    units = [elem.strip() for elem in lines[3][1:].split('  ') if elem.strip()]
    names = [elem.strip() for elem in lines[2][1:].split('  ') if elem.strip()]
    channels = [elem.strip() for elem in lines[1][1:].split('  ') if elem.strip()]
    traces = [elem.strip() for elem in lines[0][1:].split('  ') if elem.strip()]

    name_pos = get_positions(lines[2][1:], names)
    channel_pos = get_positions(lines[1][1:], channels)
    trace_pos = get_positions(lines[0][1:], traces)
    tmp = [(traces[dummy[2]], channels[dummy[1]], names[dummy[0]]) for dummy in position_equalizer(name_pos, channel_pos, trace_pos)]
    keys = [a+b for a,b in zip(tmp, zip(units, idx))]
    return keys

def parse_ficurve_key(block, file):
    lines = [linecache.getline(file, i + 1) for i in range(block.start+1, block.end)]
    units = [elem.strip() for elem in lines[1][1:].split('  ') if elem.strip()]
    names = [elem.strip() for elem in lines[0][1:].split('  ') if elem.strip()]
    return zip(names, units)


def parse_key(block, file):
    """
    Parses the key information from the lines extracted from a relacs file.

    :param lines: lines form a relacs data file
    :return: parsed key information as a list of tuples
    """
    lines = [linecache.getline(file, i + 1) for i in range(block.start, block.end)]
    return zip(*[[e.strip() for e in line[1:].split("  ") if len(e.strip()) > 0] for line in lines[1:]])


class KeyFactory:
    """
    KeyFactory class that gets a list of FileRange namedtuple objects and a filename. Can be called with
    the python with statement to produce the key for a given other FileRange object (usually FileRange objects
    refering to data). The returned key is the immediately preceeding key in the file.

    Example:

    >>> with key_factory(FileRange(start=20, end=50, type='data')) as key:
    >>>     ...
    """
    def __init__(self, keys, file):
        """

        :param keys: list of namedtuple FileRange objects with fields start and end
        :param file: filename the FileRange refer to
        """
        self.keys = sorted(keys, key=lambda e: e.start)
        self.current_key = None
        self.file = file

    def __call__(self, elem):
        if type(elem) == types.ListType:
            self.current_key = None
            return self
        else:
            self.current_key = self.keys[0]
            i = 1
            while i < len(self.keys) and self.keys[i].start < elem.start:
                self.current_key = self.keys[i]
                i += 1
            return self

    def __enter__(self):
        return self.current_key

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


