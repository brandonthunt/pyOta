import tkinter as tk
import uhd
import telnetlib
import numpy as np
import queue
import time
import threading
import argparse
import struct       # for debug

# ~~~ NOTE: Input .bin files are read as int32s with alternating real and imag samples ~~~
# globals
INIT_DELAY = 0.25               # Delay before transmission by 0.25 seconds to ensure to initial underruns occur
TNSLEEP = 0.1
ALLGPIO = [2, 3, 4, 5, 6, 7]

# Create Object
class txFromRadio(tk.Tk):
    # --- attributes ---
    # empty list for streamed samples
    stream_buff = []            # placeholder for our buffer of streamed samples
    was_clicked = False         # Is set to true upon button press. Ends recording after final pkt rx.
    pMod = 0.01                 # default power level to -20dB
    pwrVec = [1, 0.1, 0.01, 0.001, 0.0001]
    pwrChangeFlag = 0
    tn = []

    # misc radio params
    rx_channels = [0]

    def __init__(self, tx_rate, fname, fc, tx_gain, debug, isPro=0, tnHost=[]):
        # create tkinter window
        super().__init__()
        self.geometry("200x320")

        # initialize radio
        self.tx_rate = tx_rate
        self.fc = fc
        self.tx_gain = tx_gain
        radio = self.initSdr()

        # if there was no radio found...
        if radio == 0:
            self.update()  # update the Tk window to prevent an error when we destroy
            self.destroy()
            msgWindow("No radio found!", "#E55", "#FFF")
            return

        # create a debug file if desired
        self.debug = debug
        if debug:
            # create debugging file
            self.f2 = open("debug/db1.bin", 'wb')

        # read file then close
        buffer = []
        with open(fname, 'rb') as f:
            while 1:
                nextSamp = f.read(4)        # how many bytes to read from file
                buffer.extend([int.from_bytes(nextSamp, byteorder='little', signed=True)])          # signed 16 bit integer
                if len(nextSamp) < 4:
                    break


        # process the metadata
        self.interp = buffer.pop(0)
        self.modType = chr(buffer.pop(0))
        self.B = buffer.pop(0)

        self.Pavg = buffer.pop(0)/1e3       # in dBm
        self.Ppeak = buffer.pop(0)/1e3      # in dBm
        self.Wtot = buffer.pop(0)           # in Hz

        if self.modType == "b":
            self.modType = "biortho"
        elif self.modType == "o":
            self.modType = "ortho"
        elif self.modType == "c":
            self.modType = "cw"
        elif self.modType == "p":
            self.modType = "pilot"
        else:
            print("unrecognized mod type!")

        # process the packet
        buffer = np.asarray(buffer, dtype=np.int32)
        if len(buffer) % 2:
            buffer = buffer[0:-1]

        bufferc = buffer[::2] + 1j*buffer[1::2]
        scaleFactor = 1/(2**32)
        self.txPacket = bufferc.astype(np.complex64)*scaleFactor                  # shift scaling from int32 -> np.complex64

        # create label and buttons
        self.rate = tk.Label(self, text="fc={:.4} kHz".format(self.fc/1e3))
        self.mt = tk.Label(self, text="modulation: "+self.modType)
        self.blab = tk.Label(self, text="mod order: {} bits/sym".format(self.B))
        self.pAvg = tk.Label(self, text="avg pwr: {} dBM".format(self.Pavg))
        self.pMax = tk.Label(self, text="max pwr: {} dBM".format(self.Ppeak))
        self.lab = tk.Label(self, text="Time elapsed: ")

        self.rate.pack()
        self.mt.pack()
        self.blab.pack()
        self.pAvg.pack()
        self.pMax.pack()
        self.lab.pack(pady=15)


        # create radio buttons for power control - Change based on hardware!
        self.pSetIdx = tk.IntVar()
        self.pSetIdx.set(2)
        if not isPro:
            self.title('HFRX Tx')
            textLab = ['0dB', '-10dB', '-20dB', '-30dB', '-40dB']
            for idx, val in enumerate(self.pwrVec):
                self.pSel = tk.Radiobutton(self, text=textLab[idx], variable=self.pSetIdx, value=idx, command=self.pSet)
                self.pSel.pack(padx=0, pady=0)
        else:
            self.title('HF-PRO Tx')
            self.tn = telnetlib.Telnet(tnHost)
            self.pMod = 1                                               # clear programmatic attenuation
            textLab = ['0dB', '-3dB', '-10dB', '-22dB', '-31.5dB']
            for idx, val in enumerate(self.pwrVec):
                self.pSel = tk.Radiobutton(self, text=textLab[idx], variable=self.pSetIdx, value=idx, command=self.pSetQueue)
                self.pSel.pack(padx=0, pady=0)

        self.button = tk.Button(self, text="End transmission")
        self.button['command'] = self.on_click
        self.button.pack(padx=16, pady=8)

        self.threading(radio)                   # begin recording via threaded process

        # begin from inside
        self.queue = queue.Queue()              # create a queue
        self.mainloop()                         # begin tkinter mainloop

    def on_click(self):
        self.lab['text'] = "Ending transmission..."
        self.was_clicked = True
        self.queue.put('terminate')

    def pSet(self):
        self.pMod = self.pwrVec[self.pSetIdx.get()]

    def pSetQueue(self):
        self.queue.put('changePwrLvl')

    def pSetPro(self, threads):
        if self.pwrChangeFlag:
            # first, set all GPIOs for maximum attenuation
            print('in pSetPro')

            self.telSetAll()

            # then, lower GPIO that should be deactivated
            lvl = self.pSetIdx.get()
            if lvl == 0:
                # no attenuation
                self.telClearAll()
            elif lvl == 1:
                # -3 dB attenuation
                self.telWrite("gpio clear 2")
                self.telWrite("gpio clear 5")
                self.telWrite("gpio clear 6")
                self.telWrite("gpio clear 7")
            elif lvl == 2:
                # -10 dB attenuation
                self.telWrite("gpio clear 2")
                self.telWrite("gpio clear 3")
                self.telWrite("gpio clear 5")
                self.telWrite("gpio clear 7")
            elif lvl == 3:
                # -22 dB attenuation
                self.telWrite("gpio clear 2")
                self.telWrite("gpio clear 3")
                self.telWrite("gpio clear 6")
            elif lvl == 4:
                # maximum attenuation; already at this level courtesy of telSetAll()
                pass

            self.pwrChangeFlag = 0
            self.queue.put('pwrLvlSet')
            self.after(100, self.checkQueue, threads)


    # use a "main" threading function to begin RX stream
    def threading(self, radio):
        threads = []        # empty list of threads

        # Call stream function
        self.t1 = threading.Thread(target=self.txFromRad, args=[radio])
        self.t1.start()
        threads.append(self.t1)

        self.t2 = threading.Thread(target=self.pSetPro, args=[threads])
        self.t2.start()
        threads.append(self.t2)

        self.after(100, self.checkQueue, threads)

    def checkQueue(self, threads):
        # update time elapsed label on window.
        self.lab['text'] = "Time elapsed: {} sec".format(int(time.time() - self.start))

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

                # appease the queue
                self.queue.task_done()

                # join all threads
                for thr in threads:
                    thr.join()

                # reset Numato to Rx mode
                if not self.tn == []:
                    self.telWrite("reset")              # reset all relays upon exit
                    self.telSetAll()                    # set all GPIO to maximize attenuation
                    self.tn.close()

                # close debugging file
                if self.debug:
                    self.f2.close()

                self.destroy()

            #
            elif self.result == 'changePwrLvl':
                print('Change pwr lvl in queue')
                self.pwrChangeFlag = 1
                self.queue.task_done()
                self.after(50, self.pSetPro, threads)

            elif self.result == 'pwrLvlSet':
                # self.t2.join()
                self.queue.task_done()
                self.after(100, self.checkQueue, threads)

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
        tx_buffer = np.zeros((buffer_samps), dtype=np.csingle)

        # initialize an empty interleaving buffer
        nsamps = 0
        idx = -1*buffer_samps
        plen = len(self.txPacket)

        # begin stream from radio
        self.start = time.time()

        # # debug
        inlv = [0]*2*buffer_samps       # 2x as long as tx_buffer to store real/imag

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
                idx = idx3-buffer_samps             # place our index in the right spot
            else:
                # normal slicing
                tx_buffer = np.array(self.txPacket[idx:idx+buffer_samps], dtype=np.complex64)

            # set programmatic attenuator
            tx_buffer *= (self.pMod)**(0.5)

            # if we are debugging, append contents of tx_buffer to file
            if self.debug:
                inlv[::2] = tx_buffer.real
                inlv[1::2] = tx_buffer.imag
                self.f2.write(struct.pack('f' * len(inlv), *inlv))

        # Send a mini-packet signalling the end of burst.
        metadata.end_of_burst = True
        streamer.send(np.zeros((1, 0), dtype=np.csingle), metadata)


    def initSdr(self):
        # TODO: throw a more intuitive error when radio is not connected
        try:
            usrp = uhd.usrp.MultiUSRP()
        except RuntimeError:
            return 0

        usrp.set_tx_rate(self.tx_rate)
        usrp.set_tx_gain(self.tx_gain)
        usrp.set_tx_freq(uhd.types.TuneRequest(self.fc), 0)
        usrp.set_time_now(uhd.types.TimeSpec(0.0))
        return usrp

    def telSetAll(self):
        # set each GPIO
        for kk in ALLGPIO:
            msg = "gpio set {}\r\n".format(kk)
            self.tn.write(msg.encode("ascii"))
            time.sleep(TNSLEEP)

    def telClearAll(self):
        # set each GPIO
        for kk in ALLGPIO:
            msg = "gpio clear {}\r\n".format(kk)
            self.tn.write(msg.encode("ascii"))
            time.sleep(TNSLEEP)

    def telWrite(self, msg):
        msg = msg + "\r\n"
        self.tn.write(msg.encode("ascii"))
        time.sleep(TNSLEEP)

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
    parser.add_argument("-n", "--name", help="name of saved file", type=str, default="no_file")
    parser.add_argument("-r", "--tx_rate", help="sampling rate of radio. Must be 100e6/{1:256} for N210 devices", type=int, default=1e6)
    parser.add_argument("-g", "--gain", help="set the tx gain [dB]", type=int, default=0)
    parser.add_argument("-f", "--center_freq", help="center frequency", type=int, required=True)
    parser.add_argument("--cw", help="transmit a carrier wave", action='store_true')
    parser.add_argument("--debug", help="save file of IQ samples sent to radio for debugging", action="store_true")
    return parser.parse_args()

if __name__=="__main__":
    # Set parameters and begin
    args = parse_args()
    rate = args.tx_rate

    # if no file, select cw
    if args.name == "no_file":
        args.cw = True

    if not args.cw:
        fname = args.name
    else:
        fname = "cw.bin"

    tx_gain = args.gain

    dir = 'txBins/'
    fc = args.center_freq
    debug = args.debug
    k = txFromRadio(rate, dir+fname, fc, tx_gain, debug)
