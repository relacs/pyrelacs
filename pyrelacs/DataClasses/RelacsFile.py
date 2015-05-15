from collections import defaultdict
import linecache
import types
import warnings
import numpy as np
from collections import namedtuple
from ast import literal_eval
from IPython import embed

from .KeyLoaders import KeyFactory, parse_key, parse_stimuli_key, parse_ficurve_key
from .MetaLoaders import parse_meta


FileRange = namedtuple('FileRange', ['start', 'end', 'type'])
MetaDataBlock = namedtuple('MetaDataBlock', ['meta', 'data'])
DataBlock = namedtuple('DataBlock', ['key', 'meta', 'data'])


def str2number(s):
    """
    From http://stackoverflow.com/questions/15357422/python-determine-if-a-string-should-be-converted-into-int-or-float
    """
    try:
        val = literal_eval(s)
        return int(val) if isinstance(val, int) else float(val)
    except:
        return s


def parse_metadata_hierarchy(structure):
    """
    Parses the structure of a relacs file into its hierarchy. The structure is given as a list of FileRanges and
    is usually obtained from :func:`parse_structure`.

    Subsequent FileRanges with type='meta' yield recursive contexts. A list of MetaDataBlock objects.
    The data field in these can either be a FileRange or a list of MetaDataBlock objects again.

    :param structure: List of FileRange objects with type either 'meta' or 'data'.
    :return:  A list of MetaDataBlock objects.
    :raise TypeError:

    See also: parse_structure
    """
    ret = []
    while len(structure) > 1:
        # pprint(structure)
        s = structure.pop(0)
        if structure[0].type == 'meta':
            ret.append(MetaDataBlock(s, parse_metadata_hierarchy(structure)))
        elif structure[0].type == 'data':
            while len(structure) > 0 and structure[0].type == 'data':
                ret.append(MetaDataBlock(s, structure.pop(0)))
        else:
            raise TypeError('Expect either data or meta element!')

    return ret


def get_properties(meta, parent=None):
    ret = set()
    if parent is None: parent = tuple()
#    print meta
    for m,v in meta.items():
        if type(v) == dict:
            ret.update(get_properties(v, parent + (m,)))
        else:
            ret.add(parent + (m,))
    return ret

def hierarchy2datablocks(hierarchy, key_factory, filename):
    ret = []
    properties = set()

    for block in hierarchy:
        newitems = parse_metadata_data_block(block, key_factory, filename)
        ret.extend(newitems)
        for block in newitems:
            properties.update(get_properties(block.meta))
    return ret, properties

def parse_metadata_data_block(block, key_factory, filename, inherited_props=None):
    """
    Parses a MetaDataBlock block from a relacs file. Each block has a meta field and a data field. The data field
    can be a list of MetaDataBlock objects again. It returns a DataBlock which contains a key, a meta, and
    a data field. The data can still be a FileRange to allow lazy loading.

    :param block: MetaDataBlock object
    :param key_factory: The KeyFactory figuring out the key for the block.
    :param filename: path to the relacs file the data is parsed from
    :param inherited_props: used for recursion. Not important on the upper level
    :return: A DataBlock
    """
    with key_factory(block.data) as key:

        meta = parse_meta(block.meta, filename)
        if inherited_props is not None:
            tmp = inherited_props.copy()
            tmp.update(meta)
            meta = tmp

        if type(block.data) == list:
            ret = []
            for b in block.data:
                ret.extend(parse_metadata_data_block(b, key_factory, filename, meta))
            return ret
        else:
            return [DataBlock(
                key=key,
                meta=meta,
                data=block.data
            )]

def parse_structure(filename, verbose=False):
    """
    Parses the structure of a relacs file.

    :param filename: path to the file
    :param verbose: print out messages during the parsing process
    :return: a list of FileRange namedtuples representing meta and data parts and a list of FileRange namedtuples with key information

    >>> structure, keys = parse_structure('stimspikes1.dat')

    """
    if verbose: print(filename, 80*'-')
    within_key = within_meta_block = within_data_block = False
    start = None
    structure = []
    keys = []
    with open(filename, 'r') as fid:
        for line_no, line in enumerate(fid):
            line = line.rstrip().lstrip()
            if not line:  # something ends
                if within_data_block:
                    structure.append(FileRange(start, line_no, 'data'))
                    within_data_block = False
                    if verbose: print("DATA END", line[:20], line_no)
                if within_meta_block:
                    structure.append(FileRange(start, line_no, 'meta'))
                    if verbose: print("META END", line[:20], line_no)
                    within_meta_block = False
                if within_key:
                    if verbose: print("KEY END", line[:20], line_no)
                    within_key = False
                    keys.append(FileRange(start, line_no, 'key'))
                start = None
                continue

            elif line.startswith('#'):
                if line.startswith('#Key'):
                    if verbose: print("KEY START", line[:20], line_no)
                    within_key = True
                    start = line_no
                    continue
                elif within_key:
                    continue
                elif within_meta_block:
                    continue
                else:  # meta block starts
                    if verbose: print("META START", line[:20], line_no)
                    start = line_no
                    within_meta_block = True
            else:  # line is not empty and does not start with #
                if within_meta_block:
                    if verbose: print("META END", line[:20], line_no)
                    structure.append(FileRange(start, line_no, 'meta'))
                    within_meta_block = False
                if within_key:
                    if verbose: print("KEY END", line[:20], line_no)
                    within_key = False
                    keys.append(FileRange(start, line_no, 'key'))

                if not within_data_block:
                    start = line_no
                    if verbose: print("DATA START", line[:20], line_no)
                    within_data_block = True

        else:  # for loop ends
            if within_data_block:
                if verbose: print("DATA END and FILE END", line[:20], line_no)
                within_data_block = False
                structure.append(FileRange(start, line_no+1, 'data'))
    return structure, keys

def relacs_file_factory(obj, mergetrials=False):
    structure, keys = parse_structure(obj.filename)
    hierarchy = parse_metadata_hierarchy(structure)

    key_factory = KeyFactory(keys, obj.filename)
    ret, fields = hierarchy2datablocks(hierarchy, key_factory, obj.filename)
    if mergetrials:
        if obj.__class__ is SpikeFile:
            ret = _merge_stimspike_trials(ret, obj.filename)
        else:
            warnings.warn("Cannot merge trials for %s" % (obj.__class__.__name__, ))

    obj.content = [(block.meta, block.key, block.data) for block in ret]

    obj.fields = defaultdict(set)
    for p, _, _ in obj.content:
        for f in fields:
            try:
                tmp = get_nested_value(p, f)
                if type(tmp) == list:
                    tmp = tuple(tmp)
                obj.fields[f].add(tmp)
            except KeyError:
                pass

    return obj

def get_unique_field(meta, pattern):
    field = meta.matching_fields(pattern)
    if  len(field) > 1:
        raise ValueError("More than one field found for !" % (pattern, ))
    elif len(field) == 1:
        return field[0]
    else:
        return None

def get_unique_value(meta, pattern):
    return getattr(meta, get_unique_field(meta, pattern))

def get_nested_value(d, k):
    if type(k) is tuple:
        ret = d
        for kk in k:
            ret = ret[kk]
        return ret
    else:
        return d[k]

def get_subkey_key_value_pairs(d, k):
    properties = get_properties(d)
    ret_key = []
    ret_val = []
    for key in properties:
        if k in key:
            ret_key.append(key)
            ret_val.append(get_nested_value(d,key))

    return ret_key, ret_val

def subkey_field_match(d, selection):
    for k, v in selection.items():
        keys, v2 = get_subkey_key_value_pairs(d,k)

        if len(keys) > 1:
            raise KeyError("Key %s is not unique!" % (k, ))
        elif len(keys) ==0:
            return  False
        elif v2[0] != v:
            return False
    else:
        return True

def exact_nested_field_match(d, selection):

    for k, v in selection.items():
        try:
            v2 = get_nested_value(d,k)
        except KeyError as e:
            return False

        if v2 != v:
            return False
    else:
        return True

def get_unique_field(meta, pattern):
    field = meta.matching_fields(pattern)
    if  len(field) > 1:
        raise ValueError("More than one field found for !" % (pattern, ))
    elif len(field) == 1:
        return field[0]
    else:
        return None

def get_unique_value(meta, pattern):
    return getattr(meta, get_unique_field(meta, pattern))

class RelacsFile(object):
    """
    Class representing a relacs data file. Contains the following fields

    **content:** a list of tuples containing the metadata (namedtuple), the keys (tuples), and the data (list)

    **fields:** dictionary that contains the possible metadata items as keys and the possible values in the data as values

    **filename:** the filename the data comes from.

    When a relacs file is instantiated, the data is not actually loaded. This happens lazyly in select where each item
    is loaded when it is requested. Once it is loaded it stays stored in the RelacsFile object.

    """

    def __init__(self, filename):
        self.filename = filename
        self = relacs_file_factory(self, mergetrials=False)

    def _finalize_selection(self, metas, keys, datas, idx):
        if len(metas) == 0:
            return None

        for i, j in enumerate(idx):
            if isinstance(datas[i], FileRange) or \
                    (type(datas[i]) == list and isinstance(datas[i][0], FileRange)):
                _, keys[i], datas[i] = self._load(j)



        return metas, keys, datas

    def data_blocks(self):
        for i in range(len(self.content)):
            yield self._load(i)

    def select(self, selection=None, **kwargs):
        ret = self._select(exact_nested_field_match, selection, **kwargs)
        if ret is None:
            return [], [], []
        else:
            return ret

    def subkey_select(self, selection=None, **kwargs):
        ret = self._select(subkey_field_match, selection, **kwargs)
        if ret is None:
            return [], [], []
        else:
            return ret


    def selectall(self):
        metas, keys, datas = list(map(list, list(zip(*self.content))))
        idx = list(range(len(self.content)))
        return self._finalize_selection(metas, keys, datas, idx)


    def _select(self, selectionfunc, selection=None, **kwargs):
        if selection is not None:
            selection.update(kwargs)
        else:
            selection = kwargs

        idx, metas, keys, datas = [], [], [], []

        for i, (meta, key, data) in enumerate(self.content):
            if selectionfunc(meta, selection):
                metas.append(meta)
                keys.append(key)
                datas.append(data)
                idx.append(i)
        return self._finalize_selection(metas, keys, datas, idx)


    def _load(self, item_index, replace=True, loadkey=True):
        meta, key, block = self.content[item_index]

        data = [linecache.getline(self.filename, i + 1) for i in range(block.start, block.end)]
        if loadkey:
            key = parse_key(key, self.filename)

        if replace:
            self.content[item_index] = (meta, key, data)

        return meta, key, data

    def __str__(self):
        tmp = []
        for k, v in self.fields.items():
            tmp.append("%s: %s" % (k, ", ".join(map(str, v)), ))
        return "%s with %i entries and field names:\n\t" % (self.__class__.__name__, len(self.content),) + "\n\t".join(
            tmp)

    def __repr__(self):
        return self.__str__()

def _merge_stimspike_trials(blocks, filename):
    ret = []


    tmp = [blocks[0].data]
    first = last = blocks[0].meta['trial']
    key = blocks[0].key
    meta = dict(blocks[0].meta)

    for i, block in enumerate(blocks):
        if i == 0: continue
        if block.meta['trial'] == last + 1:
            last += 1
            tmp.append(block.data)
        else:
            meta['trial'] = (first, last + 1)
            ret.append(DataBlock(meta=meta, key=key, data=tmp))

            tmp = [block.data]

            key = block.key
            meta = dict(block.meta)
            first = last = meta['trial']
    else:
        if len(tmp) > 0:
            meta['trial'] = (first, last + 1)
            ret.append(DataBlock(meta=meta, key=key, data=tmp))
    return ret

class SpikeFile(RelacsFile):
    def __init__(self, filename, mergetrials=True):
        self.filename = filename

        self = relacs_file_factory(self, mergetrials=mergetrials)

    def _load(self, item_index, replace=True, loadkey=True):
        meta, key, block = self.content[item_index]

        data = []
        if type(block) == list:
            for b in block:
                tmp = np.array([float(linecache.getline(self.filename, i + 1)) for i in range(b.start, b.end)])
                data.append(tmp)
        elif isinstance(block, FileRange):
            data = np.array([float(linecache.getline(self.filename, i + 1)) for i in range(block.start, block.end)])

        if loadkey:
            key = parse_key(key, self.filename)

        if replace:
            self.content[item_index] = (meta, key, data)

        return meta, key, data

class StimuliFile(RelacsFile):
    def __init__(self, filename):
        super(StimuliFile, self).__init__(filename)

    def _load(self, item_index, replace=True):
        meta, key, data = super(StimuliFile, self)._load(item_index, replace=False, loadkey=False)
        key = parse_stimuli_key(key, self.filename)
        data = [[str2number(elem.strip()) for elem in line.split('  ') if elem.strip()] for line in data]
        if replace:
            self.content[item_index] = (meta, key, data)
        return meta, key, data

class BeatFile(RelacsFile):
    def __init__(self, filename):
        super(BeatFile, self).__init__(filename)

    def _load(self, item_index, replace=True):
        meta, key, data = super(BeatFile, self)._load(item_index, replace=False, loadkey=False)
        key = parse_key(key, self.filename)
        data = [[str2number(elem.strip()) for elem in line.strip().split()] for line in data]
        if replace:
            self.content[item_index] = (meta, key, data)
        return meta, key, data

class TraceFile(RelacsFile):
    def __init__(self, filename):
        super(TraceFile, self).__init__(filename)

    def _load(self, item_index, replace=True):
        meta, key, data = super(TraceFile, self)._load(item_index, replace=False, loadkey=True)
        data = np.asarray([[str2number(elem.strip()) for elem in line.strip().split()] for line in data])
        if replace:
            self.content[item_index] = (meta, key, data)
        return meta, key, data

class EventFile(RelacsFile):
    def __init__(self, filename):
        super(EventFile, self).__init__(filename)

    def _load(self, item_index, replace=True):
        meta, key, data = super(EventFile, self)._load(item_index, replace=False, loadkey=False)
        key = parse_key(key, self.filename)
        data = np.asarray([[str2number(elem.strip()) for elem in line.strip().split()] for line in data])
        if replace:
            self.content[item_index] = (meta, key, data)
        return meta, key, data

class FICurveFile(StimuliFile):
    def __init__(self, filename):
        super(FICurveFile, self).__init__(filename)

    def _load(self, item_index, replace=True):
        meta, key, data = super(StimuliFile, self)._load(item_index, replace=False, loadkey=False)
        key = parse_ficurve_key(key, self.filename)
        data = np.array([[str2number(elem.strip()) for elem in line.split('  ') if elem.strip()] for line in data])
        if replace:
            self.content[item_index] = (meta, key, data)
        return meta, key, data

def read_info_file(file_name):
    """
    By dr Groovy, acutally.
    Reads the info file and returns the stored metadata in a dictionary.
    The dictionary may be nested.
    @param file_name:  The name of the info file.
    @return: dictionary, the stored information.
    """
    information = []
    root = {}
    with open(file_name, 'r') as f:
        lines = f.readlines()
        for l in lines:
            if not l.startswith("#"):
                continue
            l = l.strip("#").strip()
            if len(l) == 0:
                continue
            if not ": " in l:
                sec = {}
                root[l] = sec
            else:
                parts = l.split(': ')
                sec[parts[0].strip()] = parts[1].strip()
    information.append(root)
    return information
