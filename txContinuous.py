import tkinter as tk
import uhd
import numpy as np
import queue
import time
from threading import *

# ~~~ NOTE: Requires input mat files to be int32s ~~~
# globals
INIT_DELAY = 0.25               # Delay before transmission by 0.25 seconds to ensure to initial underruns occur

# Create Object
class txFromRadio(tk.Tk):
    # --- attributes ---
    # empty list for streamed samples
    stream_buff = []            # placeholder for our buffer of streamed samples
    was_clicked = False          # Is set to true upon button press. Ends recording after final pkt rx.

    # misc radio params
    # TODO: add argparse/kwargs here to parse the input
    rx_rate = 1e6
    rx_channels = [0]
    rx_gain = 60
    fc = 6116e3

    def __init__(self, rx_rate, fname, fc):
        # create tkinter window
        super().__init__()
        self.geometry("200x50")

        # create label and button
        self.lab = tk.Label(self, text="Time elapsed: ")
        self.lab.pack()

        self.button = tk.Button(self, text="End recording")
        self.button['command'] = self.on_click
        self.button.pack()

        # initialize radio
        self.rx_rate = rx_rate
        self.fc = fc
        radio = self.initSdr(fc)

        # load the transmit file
        f = open(fname, 'rb')

        # parse relevant data
        # self.B = int.from_bytes(f.read(1), byteorder='little', signed=True)       # save any metadata in the file
        buffer = []

        # read file
        while 1:
            nextSamp = f.read(4)        # how many bytes to read from file
            buffer.extend([int.from_bytes(nextSamp, byteorder='little', signed=True)])          # signed 16 bit integer
            if len(nextSamp) < 4:
                break

        self.interp = buffer.pop(0)
        self.modType = buffer.pop(0)
        self.B = buffer.pop(0)

        buffer = np.asarray(buffer, dtype=np.int32)
        if len(buffer) % 2:
            buffer = buffer[0:-1]

        bufferc = buffer[::2] + 1j*buffer[1::2]
        self.txPacket = bufferc.astype(np.complex64)/(2**32)                  # shift scaling from int32 -> np.complex64
        #self.txPacket2 = np.exp(2j*np.pi*2000*np.arange(1e5)/1e6)

        self.threading(radio)                   # begin recording via threaded process

        # begin from inside
        self.queue = queue.Queue()              # create a queue
        self.mainloop()                         # begin tkinter mainloop

    def on_click(self):
        self.lab['text'] = "Ending transmission..."
        self.was_clicked = True
        self.queue.put('terminate')

    # use a "main" threading function to begin RX stream
    def threading(self, radio):
        threads = []        # empty list of threads

        # Call stream function
        t1 = Thread(target=self.txFromRad, args=[radio])
        t1.start()
        threads.append(t1)
        self.after(100, self.checkQueue, threads)

    def checkQueue(self, threads):
        """ Check if there is something in the queue. """
        try:
            # retrieve the queue
            self.result = self.queue.get(False)
        except queue.Empty:
            # poll the queue again after 100us if the queue was empty
            self.after(100, self.checkQueue, threads)
        else:
            # if we do NOT get an exception (queue not empty), then check queue.
            if self.result == 'terminate':
                print("Acknowledging button press... transmission complete.")
                self.queue.task_done()
                for thr in threads:
                    thr.join()
                self.destroy()
            else:
                # "catch" unknown queue elements.
                print('unknown item in queue...')

    # stream function
    def txFromRad(self, radio):
        # Initialize stream settings for radio
        metadata = uhd.types.TXMetadata()
        metadata.time_spec = uhd.types.TimeSpec(radio.get_time_now().get_real_secs() + INIT_DELAY)
        metadata.has_time_spec = True
        st_args = uhd.usrp.StreamArgs("fc32", "sc16")
        st_args.channels = [0]
        streamer = radio.get_tx_stream(st_args)
        buffer_samps = streamer.get_max_num_samps()
        tx_buffer = np.zeros((1, buffer_samps), dtype=np.complex64)

        # initialize an empty interleaving buffer
        nsamps = 0
        idx = 0
        plen = len(self.txPacket)

        # begin stream from radio
        start = time.time()

        while not self.was_clicked:
            nsamps += streamer.send(tx_buffer, metadata)          # collect nsamps samples per loop

            # Handle circbuffering
            idx += buffer_samps
            if idx + buffer_samps > plen:
                # wraparound slicing
                idx2 = plen
                idx3 = idx + buffer_samps - plen
                eop = self.txPacket[idx:idx2]
                bop = self.txPacket[0:idx3]
                tx_buffer = np.array(np.concatenate([eop, bop]), dtype=np.complex64)
            else:
                # normal slicing
                tx_buffer = np.array(self.txPacket[idx:idx+buffer_samps], dtype=np.complex64)

            # update time elapsed label on window.
            self.lab['text'] = "Time elapsed: {} sec".format(int(time.time()-start))

        # Send a mini-packet signalling the end of burst.
        metadata.end_of_burst = True
        streamer.send(np.zeros((1, 0), dtype=np.complex64), metadata)


    def initSdr(self, fc):
        # TODO: throw a more intuitive error when radio is not connected
        usrp = uhd.usrp.MultiUSRP()
        usrp.set_tx_rate(self.rx_rate)
        usrp.set_tx_freq(uhd.types.TuneRequest(fc), 0)
        usrp.set_time_now(uhd.types.TimeSpec(0.0))
        return usrp

if __name__=="__main__":
    # Set parameters and begin
    rate = 1e6
    fname = '100k_8_20seg_chan0_May11_22.bin'
    dir = 'txBins/'
    fc = 6116e3
    k = txFromRadio(rate, dir+fname, fc)