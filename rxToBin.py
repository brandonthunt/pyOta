import uhd
import numpy as np
import argparse
from scipy.io import FortranFile
from matplotlib import pyplot as plt
import time
import os
import tkinter as tk
import struct

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--args", default="", type=str)
    parser.add_argument("-o", "--output-file", type=str, required=True)
    parser.add_argument("-f", "--freq", type=float, required=True)
    parser.add_argument("-r", "--rate", default=1e6, type=float)
    parser.add_argument("-d", "--duration", default=5.0, type=float)
    parser.add_argument("-c", "--channels", default=0, nargs="+", type=int)
    parser.add_argument("-g", "--gain", type=int, default=10)
    return parser.parse_args()

def saveFileOfDur(freq, fname, duration, rate):
    # args = parse_args()

    usrp = uhd.usrp.MultiUSRP()
    num_samps = int(np.ceil(duration * rate))
    channels = [0]
    samps = np.zeros(num_samps)
    samps = usrp.recv_num_samps(num_samps, freq, rate, channels, 70)

    # f = FortranFile(fname, 'w')
    f = open(fname, 'wb')
    inlv = [0]*2*num_samps
    inlv[::2] = samps[0, :].real
    inlv[1::2] = samps[0, :].imag

    # f.write_record(np.array(inlv, dtype=float))
    f.write(struct.pack('f' * len(inlv), *inlv))
    f.close()
    print('Done')

# --- liveSpecg ---
# A live spectrogram of the rx space centered at fc and extending to +/- W/2.
# Smoothing averages successive f-domain measurements together to smooth the noise.
def liveSpecg(fc, W, smoothing=20):
    duration = 0.25     # update 4 times per second
    # fcd = fc+W/2        # remove DC spike by shifting fc to fc_dash
    # Wd = W*2            # We must widen our window by restricting our view
    rate = 1e6

    # Init our radio
    usrp = uhd.usrp.MultiUSRP()
    num_samps = int(np.ceil(duration * rate))

    # decimation = int(np.round(rate / W))
    decimation = 1
    f = np.linspace(-W/2, W/2, int(np.round(num_samps/decimation)))

    plt.ion()
    fig = plt.figure()
    ax = fig.add_subplot(111)
    line1, = ax.plot(f, f)  # Returns a tuple of line objects, thus the comma

    while 1:
        channels = [0]
        samps = np.zeros(num_samps)
        samps = usrp.recv_num_samps(num_samps, freq, rate, channels, 70)

        #sd = samps[0, range(0, num_samps, decimation)]
        sd = samps[0, :]
        Sf = 10*np.log10(np.abs(np.fft.fft(sd)))
        line1.set_ydata(Sf)
        plt.ylim(-30, 20)
        fig.canvas.draw()
        fig.canvas.flush_events()



if __name__ == "__main__":
    fname = "rxOfDur.bin"
    freq = 6116000
    duration = 1
    rate = 1e6
    saveFileOfDur(freq, fname, duration, rate)
