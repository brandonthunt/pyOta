import tkinter as tk
from threading import *
import uhd
import numpy as np
import os
import queue
import struct
import argparse
import time
import uuid


# Define object
class streamFromRadio(tk.Tk):
    # --- attributes ---
    # empty list for streamed samples
    stream_buff = []            # placeholder for our buffer of streamed samples
    was_clicked = False         # Is set to true upon button press. Ends recording after final pkt rx.
    fileNum = 0

    # misc radio params
    rx_channels = [0]           # single channel rx

    # flags
    isOverLength = 0            # set when the file first exceeds the max length limit
    fileSizeOverAck = 0         # set to prevent multiple 'file overlength' writes to the queue
    midFileWriteFlag = 0        # set to prevent multiple file open/closes from checkQueue() function calls
    recordTimeout = 0           # set to indicate a record timeout has occurred
    timeOutAck = 0              # set to prevent multiple timeout messages from getting added to the queue

    def __init__(self, rx_rate, fname, fc, rx_gain, fif, fileSizeLim=0, timeOutMins=0):
        # create tkinter window
        super().__init__()
        self.geometry("200x75")

        # create labels and button
        self.lab = tk.Label(self, text="Filesize: ")
        self.lab.pack(pady=2)

        self.timeElapseLab = tk.Label(self, text="Time Elapsed: ")
        self.timeElapseLab.pack(pady=2)

        self.button = tk.Button(self, text="End recording", bg='#E55', activebackground="#E55")
        self.button['command'] = self.on_click
        self.button.pack()

        # initialize radio; copy inputs to Tk object
        self.rx_rate = rx_rate
        self.fif = fif
        self.fc = fc+self.fif
        self.rx_gain = rx_gain
        self.fileSizeLim = fileSizeLim
        self.radio = self.initSdr()

        # if there was no radio found...
        if self.radio == 0:
            self.update()                       # update the Tk window to prevent an error when we destroy
            self.destroy()
            msgWindow("No radio found!", "#E55", "#FFF")
            return

        # index filename if a filesize limit is specified
        self.fNameIn = fname
        self.createFile()

        # handle timings
        self.timeOutLen = timeOutMins*60        # seconds
        self.tStart = time.time()               # record start time

        # begin from inside
        self.threading()                        # begin recording via threaded process
        self.queue = queue.Queue()  # create a queue
        self.mainloop()                         # begin tkinter mainloop

    def on_click(self):
        self.lab['text'] = "Ending recording..."
        self.was_clicked = True
        self.queue.put('terminate')

    # use a "main" threading function to begin RX stream
    def threading(self):
        # Call stream function
        self.t1 = Thread(target=self.streamFromRad, args=[self.radio])
        self.t1.start()
        self.after(100, self.checkQueue)

    def checkQueue(self):
        # Update tk labels
        self.lab['text'] = "Filesize: {:.1f} MB".format(os.path.getsize(self.f.name) / 1e6)
        self.timeElapseLab['text'] = "Time Elapsed: {:.1f} sec / {:.0f}".format(time.time()-self.tStart,
                                                                                self.timeOutLen)

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
                print("Acknowledging termination request...")
                self.queue.task_done()
                self.t1.join()
                self.destroy()
                if self.recordTimeout:
                    msgWindow("Time limit reached.")

            elif self.result == 'fileSizeLimReached':
                # all we do here is set the flag and jump out
                self.isOverLength = 1
                self.queue.task_done()
                self.after(100, self.checkQueue)

            elif self.result == 'newFileReady':
                # reset all of our flags so we may resume streaming
                self.isOverLength = 0
                self.midFileWriteFlag = 0
                self.fileSizeOverAck = 0
                print('Writing to new file with name ' + self.f.name)
                self.queue.task_done()
                self.after(100, self.checkQueue)

            elif self.result == 'recordTimeout':
                # set flag and jump out
                self.recordTimeout = 1
                self.queue.put('terminate')
                self.after(100, self.checkQueue)

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

        # init a metadata var
        metadata = uhd.types.RXMetadata()
        had_an_overflow = False

        # initialize an empty interleaving buffer
        inlv = [0] * 2 * buffer_samps

        # call recv() once to begin receiving. This data is discarded because it contains a transient.
        samps = streamer.recv(recv_buffer, metadata)
        nsamps = 0

        # begin stream from radio
        while not self.was_clicked and not self.recordTimeout:
        #while self.queue.empty():
            if not self.isOverLength:
                nsamps += streamer.recv(recv_buffer, metadata)          # collect nsamps samples per loop

                # interleave real and imaginary to inlv vector.
                inlv[::2] = recv_buffer[0, :].imag
                inlv[1::2] = recv_buffer[0, :].real

                # write 32-bit floats to file; update filesize label on window.
                self.f.write(struct.pack('f'*len(inlv), *inlv))         # 'f' datatype == float (4 bytes) for each real and imag

                recv_buffer = np.zeros((1, buffer_samps), dtype=np.complex64)

                # calculate filesize, check for overlength
                if self.fileSizeLim:
                    fSize = os.path.getsize(self.f.name) / 1e6
                    if fSize > self.fileSizeLim and not self.fileSizeOverAck:
                        self.fileSizeOverAck = 1
                        self.queue.put('fileSizeLimReached')

                # calculate time elapsed, check for timeout
                if self.timeOutLen:
                    tElapse = time.time() - self.tStart
                    if tElapse > self.timeOutLen and not self.timeOutAck:
                        self.timeOutAck = 1
                        self.queue.put('recordTimeout')

            else:
                if not self.midFileWriteFlag:
                    self.midFileWriteFlag = 1

                    # close file
                    self.f.close()

                    # create new file with proper naming convention
                    # fname = self.fnameTrunc + '_' + str(self.fileNum) + '.bin'

                    # initialize file
                    # self.fileNum += 1
                    self.createFile()
                    self.queue.put('newFileReady')
                    self.checkQueue()
                else:
                    pass


    def initSdr(self):
        try:
            usrp = uhd.usrp.MultiUSRP()
        except RuntimeError:
            return 0

        usrp.set_rx_rate(self.rx_rate)
        usrp.set_rx_freq(uhd.types.TuneRequest(self.fc), 0)
        usrp.set_rx_gain(self.rx_gain)
        return usrp

    def createFile(self):
        if self.fileSizeLim:
            self.fnameTrunc = self.fNameIn[:-4]
            macFormat = [''.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff) for ele in range(0, 8 * 6, 8)][::-1])]
            macString = ''.join(macFormat)
            fname = self.fnameTrunc + '_' + str(self.fileNum) + '_' + macString[-6:] + '.bin'
        else:
            fname = self.fNameIn

        # initialize file
        self.f = open(fname, 'wb')

        # write IF, fc to beginning of metadata
        fMetadata = np.array([self.fc-self.fif, self.fif, self.rx_rate], dtype=np.int32)
        self.f.write(struct.pack('f' * len(fMetadata), *fMetadata))
        self.fileNum += 1


class msgWindow(tk.Tk):
    def __init__(self, message, bgcolor="#DDD", fgcolor="#000"):
        # create tkinter window
        super().__init__()
        self.geometry("200x75")

        # create labels and button
        self.lab = tk.Label(self, text=message, fg=fgcolor, bg =bgcolor)
        self.lab.pack(pady=10)

        self.button = tk.Button(self, text="Close window")
        self.button['command'] = self.on_click
        self.button.pack()

        self.configure(bg=bgcolor)
        self.mainloop()

    def on_click(self):
        self.destroy()




def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--name", help="name of saved file", type=str, default="rx.bin")
    parser.add_argument("-r", "--rx_rate", help="sampling rate of radio. Must be 100e6/{1:256} for N210 devices", type=int, default=1000000)
    parser.add_argument("-o", "--offset_freq", help="offset frequency in Hz from carrier to avoid DC spike", type=float, default=100000)
    parser.add_argument("-g", "--gain", help="set the rx gain [dB]",type=int, default=8)
    parser.add_argument("-f", "--center_freq", help="center frequency in Hz", type=float, required=True)
    return parser.parse_args()

def streamRxLauncher(rx_rate, fname, fc, rx_gain, offset_freq, fsCutoff=2**9, tRecord = 10):
    # helper function used to manage launching.
    # default value of 2^9 = 512 MB which is the filesize cutoff we are striving for
    tRecord = 3
    tStart = time.time()
    winNum = 0
    fnameTrunc = fname[:-4]

    while tStart - time.time() < tRecord*60:
        fnameItr = fnameTrunc  + '_' + str(winNum) + '.bin'  # final 4 characters in fname are ".bin"; ignore so we can index
        winNum += 1  # index winNum for next loop
        k = streamFromRadio(rx_rate,
                            fnameItr,
                            fc,
                            rx_gain,
                            offset_freq,
                            fsCutoff)

if __name__=="__main__":
    # Set parameters and begin
    args = parse_args()

    # assign args from parser
    rate = args.rx_rate
    fif = args.offset_freq
    fname = args.name
    rx_gain = args.gain
    # dir = "/home/hf/Documents/pyRad/pyOta/rxBins/"
    dir = os.getcwd() + '/rxBins/'
    fc = args.center_freq

    with open(dir+fname, 'wb') as f:
        pass

    k = streamFromRadio(rate, dir+fname, fc, rx_gain, fif)