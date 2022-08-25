#!/usr/bin/env python3
import os
import os.path
import sys
import time
from txContinuous import txFromRadio as tfr
import datetime as dt
import queue
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import uuid
import telnetlib

HOST = "192.168.10.64"  # static IP of Numato controller
TNSLEEP = 0.1  # sleep time after passing each command to block for telnet
MINFREQ_6 = 20500000
MINFREQ_5 = 13800000
MINFREQ_4 = 10350000
MINFREQ_3 = 7500000
MINFREQ_2 = 5300000


class ezRxWindow(tk.Tk):
    # --- attributes ---
    # empty list for streamed samples
    tx_rate = 100e6 / 100
    tx_gain = 0
    fname = []
    dir = 'txBins/'
    isHFPRO = 0                             # default equipment type
    tn = []                                 # empty telnet object buffer

    def __init__(self):
        # create tkinter window
        super().__init__()
        self.geometry("200x280")
        self.title('Tx')

        # initialize Queue and begin polling
        self.queue = queue.Queue()
        self.after(100, self.checkQueue)

        """ GUI/HMI Interactivity Construction """
        # CW checkmark
        self.ftLabel = tk.Label(self, text="Select Tx File:")
        self.ftLabel.pack()
        self.cwFlag = tk.IntVar()
        self.cwTick = tk.Checkbutton(self, text="Carrier Wave", variable=self.cwFlag, onvalue=1, offvalue=0,
                                     command=self.selCw)
        self.cwTick.pack()

        # Filebrowser option
        self.fbButton = tk.Button(self, text="Choose file...", command=self.browseFiles)
        self.fbButton.pack()

        # waveform select label
        self.selLab = tk.Label(self, text="Selected file: ")
        self.selLab.pack()
        self.wvSelLab = tk.Label(self, text="none")
        self.wvSelLab.pack()

        # separator
        sep = ttk.Separator(self, orient="horizontal")
        sep.pack(fill='x', padx=10)

        # fc label and input
        fclab = tk.Label(text="Center frequency [kHz]:")
        fclab.pack()
        self.fcIn = tk.Text(self, height=1, width=20, pady=1)
        self.fcIn.pack(pady=6)

        # Transmit waveform button
        sep2 = ttk.Separator(self, orient="horizontal")
        sep2.pack(fill='x', padx=10)
        self.txButton = tk.Button(self, text="Begin transmit", command=self.on_click)
        self.txButton.pack(pady=6)

        # seperator 3
        sep3 = ttk.Separator(self, orient="horizontal")
        sep3.pack(fill='x', padx=10)

        # Input statuses
        err = tk.Label(self, text="Status:")
        err.pack()
        self.statusLab = tk.Label(self, text="")
        self.statusLab.pack()

        # begin mainloop
        self.mainloop()

    # --- Select CW checkbox ---
    def selCw(self):
        # self.fbButton.config(state=["disabled" if self.cwFlag.get() else "normal"])
        if self.cwFlag.get():
            self.fbButton.configure(state="disabled")
            self.fname = "cw.bin"
            self.wvSelLab['text'] = 'Carrier Wave'
        else:
            self.fbButton.configure(state="normal")

    # --- filebrowser function ---
    def browseFiles(self):
        fnameAndDir = filedialog.askopenfilename(initialdir=self.dir,
                                                 title="Select Tx File",
                                                 filetypes=[("Waveform files", "*.bin")])
        try:
            fname = os.path.basename(fnameAndDir)  # if filebrowser is closed, we get a TypeError
        except TypeError:
            fname = "Invalid Selection!"

        self.wvSelLab['text'] = fname
        self.fname = fname

    # --- Tasks to perform on button click ---
    def on_click(self):
        self.was_clicked = True
        self.queue.put('start_tx')

    # Ensure parameters from GUI have been properly transferred
    def assertParameters(self):
        # read fc input and throw error if invalid
        try:
            fchz = float(self.fcIn.get("1.0", "end-1c"))
            self.fc = 1000 * fchz

            # verify input falls into HF band
            if self.fc > 30e6:
                self.statusLab['text'] = "Center freq. too high!"
                self.statusLab['fg'] = "#e00"
                return 1
            elif self.fc < 3e6:
                self.statusLab['text'] = "Center freq. too low!"
                self.statusLab['fg'] = "#e00"
                return 1

        except ValueError:
            self.statusLab['text'] = "Invalid center frequency!"
            self.statusLab['fg'] = "#e00"
            return 1

        # check file is selected
        if self.fname == [] or self.fname == "Invalid Selection!":
            self.statusLab['text'] = "Invalid filename!"
            self.statusLab['fg'] = "#e00"

    def checkQueue(self):
        """ Check if there is something in the queue. """
        try:
            # retrieve the queue
            self.result = self.queue.get(False)
        except queue.Empty:
            # poll the queue again after 100us if the queue was empty
            self.after(100, self.checkQueue)
        else:
            # if we do NOT get an exception (queue not empty), then check queue.
            if self.result == 'start_tx':
                print("Acknowledging button press... beginning transmission")
                errFlag = self.assertParameters()

                # if an error was thrown when assigning parameters, return to polling queue
                if errFlag:
                    self.queue.task_done()
                    self.checkQueue()
                    return

                # Check hardware type and initialize
                self.txButton['text'] = "Scanning equipment..."
                self.txButton.configure(state="disabled")
                self.update()
                isHFRX = os.system("ping -c 1 " + HOST)
                if isHFRX:
                    print("No numato controller found; HFRX detected")
                    # no code here; HFRX interfaces directly to laptop
                else:
                    print("Numato controller found; HFPRO detected")
                    self.isHFPRO = 1
                    self.txButton['text'] = "Connecting to HFPRO..."
                    self.statusLab['text'] = "Connecting..."
                    self.statusLab['fg'] = "#aaa"
                    self.update()
                    self.initHFPROtx()
                    self.tn.close()

                # Write to logger file
                self.writeLog()

                # Destroy current window, spawn stream-record window from rxContinuous.py
                self.queue.task_done()
                self.destroy()
                tfr(self.tx_rate,                   # transmit sampling rate
                    self.dir + self.fname,          # filenme
                    self.fc,                        # center frequency
                    self.tx_gain,                   # transmit gain
                    0,                              # debug enable
                    self.isHFPRO,                   # are we using HFPRO or HFRX?
                    HOST)                           # provide telnet object (or empty buffer if HFRX)
            else:
                # "catch" unknown queue elements.
                print('unknown item in queue...')

    def writeLog(self):
        # Open/create text file for logging
        macFormat = [':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff) for ele in range(0, 8 * 6, 8)][::-1])]
        macString = ''.join(macFormat)

        macunFormat = [''.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff) for ele in range(0, 8 * 6, 8)][::-1])]
        macunString = ''.join(macunFormat)

        utc = dt.datetime.utcnow()
        self.utcStr = utc.strftime("_%b%d_%H%M")
        with open(self.dir + 'txLog_' + macunString[-6:] + '.txt', 'a') as f:
            # fairly jank MAC address reformatting
            f.write('\n')
            f.write('==================================================\n')
            row = "New Transmission started at " + self.utcStr[1:] + " from machine with MAC of " + macString + ".\n"
            f.write(row)
            row = "fc = " + str(self.fc) + "Hz\n"
            f.write(row)
            row = "selected file: " + self.fname + "\n"
            f.write(row)
            row = "equipment type: " + ("HFPRO\n" if self.isHFPRO else "HFRX\n")
            f.write(row)
            f.write('==================================================\n')

    def initHFPROtx(self):
        self.tn = telnetlib.Telnet(HOST)
        time.sleep(TNSLEEP)
        self.telRead("\n")

        #  - read state of internal/external amp select -
        # NOTE: "read" command configures GPIO 0 as an input
        while 1:
            self.telWrite("gpio read 0")
            state = str(self.tn.read_eager())
            print(state)
            if "0" in state:
                # Use internal amp
                isInternalAmp = 1
                print('Using internal amp')
                break
            elif "1" in state:
                # use external
                isInternalAmp = 0
                print('Using external amp')
                break

        # - Set associated relays -
        self.telWrite("reset")  # sets all relays == 0
        if isInternalAmp:
            self.telWrite("relay on 1")  # turn on internal amplifier
        else:
            self.telWrite("relay on 0")  # Select external amplifier
            self.telWrite("relay on 9")  # Select external RF path

        # set static Tx relays
        self.telWrite("relay on 8")  # select Tx hardware path
        self.telWrite("relay on A")  # enable PTT (#A = 10 in Hex)

        # Enable attenuator and set to max attenuation
        self.telWrite("gpio set 1")  # enables attenuator
        for k in range(2, 8):
            self.telWrite("gpio set {}".format(k))  # enable each level of attenuation

        # - Configure Filters! -
        fc = self.fc
        if fc >= MINFREQ_6:
            filtSel = 6
        elif fc >= MINFREQ_5:
            filtSel = 5
        elif fc >= MINFREQ_4:
            filtSel = 4
        elif fc >= MINFREQ_3:
            filtSel = 3
        elif fc >= MINFREQ_2:
            filtSel = 2
        else:
            filtSel = 1

        self.telWrite("relay on {}".format(filtSel+1))      # filter indexes are 1 higher than coresponding band


    def telRead(self, msg):
        rxmsg = self.tn.read_until(msg.encode("ascii"))
        time.sleep(TNSLEEP)
        return str(rxmsg)

    def telWrite(self, msg):
        msg = msg + "\r\n"
        self.tn.write(msg.encode("ascii"))
        time.sleep(TNSLEEP)


# If we run this file as the main script...
if __name__ == "__main__":
    try:
        sys.path.index('/usr/local/lib/python3/dist-packages/python')
    except:
        sys.path.append('/usr/local/lib/python3/dist-packages/python')

    ezRxWindow()
