from IPython import embed
import nix
import numpy as np

def trial_iterator(multi_tag):
    traces = {r.name:np.asarray(r.data) for r in multi_tag.references if r.dimensions[0].dimension_type.name == 'Set'}

    sample_interv = {r.name:r.dimensions[0].sampling_interval for r in multi_tag.references if r.dimensions[0].dimension_type.name == 'Sample'}
    print sample_interv
    print traces
    positions =  multi_tag.positions[:]
    extents =  multi_tag.extents[:]
    for i, (p, e) in enumerate(zip(positions, extents)):
        ret = {}
        for ref_no, r in enumerate(multi_tag.references):
            dim = r.dimensions[0]
            if dim.dimension_type.name == 'Set':
                ret[r.name] = traces[r.name][(traces[r.name] >= p) & (traces[r.name] <= p+e)]
            else:
                try:
                    ret[r.name] = multi_tag.retrieve_data(i, ref_no)
                except:
                    embed()
            ret['t'] = np.arange(p,p+e+sample_interv['V-1'],sample_interv['V-1'])
        yield ret

    #
    # for p, e in zip(np.asarray(multi_tag.positions.data), np.asarray(multi_tag.extents.data)):
    #     ret = dict()
    #     for r in multi_tag.references:
    #         dim = r.dimensions[0]
    #
    #         if dim.dimension_type.name == 'Set':
    #             ret[r.name] = traces[r.name][(traces[r.name] >= p) & (traces[r.name] <= p+e)]
    #         elif dim.dimension_type.name == 'Sample':
    #             pos = int(p/sample_interv[r.name])
    #             ext = int(e/sample_interv[r.name])
    #             ret[r.name] = traces[r.name][pos:pos+ext]
    #         ret['t'] = np.arange(p,p+e,sample_interv['V-1'])

if __name__=="__main__":
    import sys
    file = sys.argv[1]
    print file

    nix_file = nix.File.open(file, nix.FileMode.ReadWrite)
    for block in [b for b in nix_file.blocks if 'FI-Curve' not in b.name]:

        for tag in block.multi_tags:
            for trial_data in trial_iterator(tag):
                embed()
                exit()
