import tkinter as tk
from threading import *
import uhd
import numpy as np
import os
import queue
import struct
import argparse

# Create Object
class streamFromRadio(tk.Tk):
    # --- attributes ---
    # empty list for streamed samples
    stream_buff = []            # placeholder for our buffer of streamed samples
    was_clicked = False          # Is set to true upon button press. Ends recording after final pkt rx.

    # misc radio params
    # TODO: add argparse/kwargs here to parse the input
    rx_rate = 1e6
    rx_channels = [0]
    fc = 6116e3

    def __init__(self, rx_rate, fname, fc, rx_gain, fif=0):
        # create tkinter window
        super().__init__()
        self.geometry("200x50")

        # create label and button
        self.lab = tk.Label(self, text="Filesize: ")
        self.lab.pack()

        self.button = tk.Button(self, text="End recording")
        self.button['command'] = self.on_click
        self.button.pack()

        # initialize radio
        self.rx_rate = rx_rate
        self.fc = fc+fif
        self.rx_gain = rx_gain
        radio = self.initSdr()


        # initialize file
        self.f = open(fname, 'wb')

        # write IF, fc to beginning of metadata
        fMetadata = np.array([fc, fif, rate], dtype=np.int32)
        self.f.write(struct.pack('f'*len(fMetadata), *fMetadata))

        # begin from inside
        self.threading(radio)  # begin recording via threaded process
        self.queue = queue.Queue()              # create a queue
        self.mainloop()                         # begin tkinter mainloop

    def on_click(self):
        self.lab['text'] = "Ending recording..."
        self.was_clicked = True
        self.queue.put('terminate')

    # use a "main" threading function to begin RX stream
    def threading(self, radio):
        # Call stream function
        t1 = Thread(target=self.streamFromRad, args=[radio])
        t1.start()

        self.after(100, self.checkQueue)

    def checkQueue(self):
        # Update tk label
        self.lab['text'] = "Filesize: {:.1f} MB".format(os.path.getsize(os.getcwd() + '/' + self.f.name) / 1e6)

        """ Check if there is something in the queue. """
        try:
            # retrieve the queue
            self.result = self.queue.get(False)
        except queue.Empty:
            # poll the queue again after 100us if the queue was empty
            self.after(100, self.checkQueue)
        else:
            # if we do NOT get an exception (queue not empty), then check queue.
            if self.result == 'terminate':
                self.f.close()
                print("Acknowledging button press... file is closed.")
                self.queue.task_done()
                self.destroy()
            else:
                # "catch" unknown queue elements.
                print('unknown item in queue...')

    # stream function
    def streamFromRad(self, radio):
        # Initialize stream settings for radio
        metadata = uhd.types.RXMetadata()
        st_args = uhd.usrp.StreamArgs("fc32", "sc16")
        st_args.channels = [0]
        streamer = radio.get_rx_stream(st_args)
        buffer_samps = streamer.get_max_num_samps()
        recv_buffer = np.zeros((1, buffer_samps), dtype=np.complex64)

        # Set the stream type and issue stream command
        stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.start_cont)   # command to start a stream for CONTINUOUS data
        stream_cmd.stream_now = True
        streamer.issue_stream_cmd(stream_cmd)

        # initialize an empty interleaving buffer
        inlv = [0] * 2 * buffer_samps

        # call recv() once to begin receiving. This data is discarded because it contains a transient.
        samps = streamer.recv(recv_buffer, metadata)
        nsamps = 0

        # begin stream from radio
        while not self.was_clicked:
        #while self.queue.empty():
            nsamps += streamer.recv(recv_buffer, metadata)          # collect nsamps samples per loop

            # interleave real and imaginary to inlv vector.
            inlv[::2] = recv_buffer[0, :].imag
            inlv[1::2] = recv_buffer[0, :].real

            # write 32-bit floats to file; update filesize label on window.
            self.f.write(struct.pack('f'*len(inlv), *inlv))

    def initSdr(self):
        # TODO: throw a more intuitive error when radio is not connected
        usrp = uhd.usrp.MultiUSRP()
        usrp.set_rx_rate(self.rx_rate)
        usrp.set_rx_freq(uhd.types.TuneRequest(self.fc), 0)
        usrp.set_rx_gain(self.rx_gain)
        return usrp

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--name", help="name of saved file", type=str, default="rx.bin")
    parser.add_argument("-r", "--rx_rate", help="sampling rate of radio. Must be 100e6/{1:256} for N210 devices", type=int, default=1000000)
    parser.add_argument("-o", "--offset_freq", help="offset frequency in KHz from carrier to avoid DC spike", type=float, default=100)
    parser.add_argument("-g", "--gain", help="set the rx gain [dB]",type=int, default=0)
    parser.add_argument("-f", "--center_freq", help="center frequency in KHz", type=float, required=True)
    return parser.parse_args()

if __name__=="__main__":
    # Set parameters and begin
    args = parse_args()

    rate = args.rx_rate
    fif = args.offset_freq
    fname = args.name
    rx_gain = args.gain
    dir = "rxBins/"
    fc = args.center_freq

    with open(dir+fname, 'wb') as f:
        pass

    # rate = 1e6
    # fif = 100e3                 # offset from carrier to remove DC spike
    # fname = 'rxCont.bin'
    # dir = 'rxBins/'
    # fc = 6116e3
    k = streamFromRadio(rate, dir+fname, fc, rx_gain, fif)