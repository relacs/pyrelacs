import numpy as np
import matplotlib.pyplot as plt
import DataLoader as dl

datapath = '2016-11-28-aa/'

# stimulus-*-traces.dat:
for info, key, data in dl.iload(datapath+'stimulus-sine-traces.dat'):
    print(info[0]['waveform'])  # look into the file to see possible metadata!
    plt.plot(data[:,0], data[:,1]) # V(t)
    plt.show()


# stimulus-*-traces.dat and stimulus-sine-spikes.dat:
spike_iter = dl.iload(datapath+'stimulus-sine-spikes.dat')
for info, key, data in dl.iload(datapath+'stimulus-sine-traces.dat'):
    _, _, spikes = next(spike_iter)
    plt.plot(data[:,0], data[:,1]) # V(t)
    plt.scatter(spikes[:,0], np.ones(len(spikes[:,0])), color='r')
    plt.show()

# load only responses of repro 'SingleStimulus' from the traces*.raw:
for info, key, time, data in dl.iload_traces(datapath, repro='SingleStimulus', before=0.0, after=0.0):
    print(info[1]['RePro'])   # these are metadata from the stimuli.dat file
    plt.plot(time, data[0])  # V(t)
    plt.show()

