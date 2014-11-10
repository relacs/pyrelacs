from IPython import embed
import nix
import numpy as np

def trial_iterator(multi_tag):
    traces = {r.name:np.asarray(r.data) for r in multi_tag.references}
    sample_interv = {r.name:r.dimensions[0].sampling_interval for r in multi_tag.references if r.dimensions[0].dimension_type.name == 'Sample'}
    for p, e in zip(np.asarray(multi_tag.positions.data), np.asarray(multi_tag.extents.data)):
        ret = dict()
        for r in multi_tag.references:
            dim = r.dimensions[0]

            if dim.dimension_type.name == 'Set':
                ret[r.name] = traces[r.name][(traces[r.name] >= p) & (traces[r.name] <= p+e)]
            elif dim.dimension_type.name == 'Sample':
                pos = int(p/sample_interv[r.name])
                ext = int(e/sample_interv[r.name])
                ret[r.name] = traces[r.name][pos:pos+ext]
            ret['t'] = np.arange(p,p+e,sample_interv['V-1'])

        yield ret


# if __name__=="__main__":
#     nix_file = nix.File.open('out.hdf5', nix.FileMode.ReadOnly)
#     recording_block = nix_file.blocks[0]
#
#     multi_tag = [t for t in recording_block.multi_tags if t.name == 'FileStimulus-run-0'][0]
#
#     fig, ax = plt.subplots()
#
#     for trial_data in trial_iterator(multi_tag):
#
#         ax.plot(trial_data['t'], trial_data['V-1'])
#         ax.plot(trial_data['spikes'], 0*trial_data['spikes'],'ok')
#     plt.show()