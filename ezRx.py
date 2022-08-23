from rxContinuous import streamFromRadio as sfr
import numpy as np
import datetime as dt
import queue
import tkinter as tk
import uuid
from threading import *

class ezRxWindow(tk.Tk):
    # --- attributes ---
    # empty list for streamed samples
    rx_gain = 8
    offset_freq = 100000
    rx_rate = 100e6/100
    fname = []
    dir = 'rxBins/'
    fileSizeCap = 2**9

    def __init__(self):
        # create tkinter window
        super().__init__()
        self.geometry("200x360")

        # initialize Queue and begin polling
        self.queue = queue.Queue()
        self.after(100, self.checkQueue)

        """ GUI/HMI Interactivity Construction """
        # create fc and textbox
        self.lab = tk.Label(self, text="Center Frequency [kHz]:")
        self.lab.pack()
        self.fcbox = tk.Text(self, height=1, width=20, pady=1)
        self.fcbox.pack(pady=5)

        # create fname label and dropdown
        self.droplab = tk.Label(self, text="Packet selection: ")
        self.droplab.pack(pady=1)
        self.clicked = tk.StringVar()
        self.clicked.set("Click to select")                                # default string
        self.nPackets = 10                                                 # number of packet options to support
        self.pktOptions = ["Packet " + str(i) for i in range(self.nPackets)]       # packet selection options
        self.drop = tk.OptionMenu(self, self.clicked, *self.pktOptions)
        self.drop.pack()

        # create recording length option
        self.rlab = tk.Label(self, text="Recording length [mins]:")
        self.rlab.pack(pady=3)
        self.recLen = tk.Text(self, height=1, width=20, pady=1)
        self.recLen.pack(pady=5)
        self.recLen.insert("1.0", '10')

        # create filesize option
        self.flab = tk.Label(self, text="Filesize limit [MB]:")
        self.flab.pack()
        self.fs = tk.Text(self, height=1, width=20, pady=1)
        self.fs.pack(pady=5)
        self.fs.insert("1.0", str(self.fileSizeCap))

        # create button & assoc. command
        self.button = tk.Button(self, text="Begin Recording")
        self.button['command'] = self.on_click
        self.button.pack(pady=14)

        self.statLab = tk.Label(self, text="Status:")
        self.statLab.pack(pady=2)
        self.errLab = tk.Label(self, text="No errors")
        self.errLab.pack()

        # begin mainloop
        self.mainloop()

    # Tasks to perform on button click
    def on_click(self):
        self.was_clicked = True
        self.queue.put('start_rec')

    # Ensure parameters from GUI have been properly transferred
    def assertParameters(self):
        # read fc input and throw error if invalid
        try:
            fchz = float(self.fcbox.get("1.0", "end-1c"))
            self.fc = 1000*fchz
        except ValueError:
            self.errLab['text'] = "Invalid center frequency!"
            self.errLab['fg'] = "#e00"
            return 1

        # some values are hardcoded. thay are unexpected to change in the future
        if self.clicked.get() == "Click to select":
            self.errLab['text'] = "Must select packet!"
            self.errLab['fg'] = "#e00"
            return 1
        else:
            fnamesel = self.clicked.get()
            fNameOpts = ["pkt" + str(i) for i in range(self.nPackets)]
            pktSel = fNameOpts[self.pktOptions.index(fnamesel)]            # shorten name to "pktX" where X \elem [0, nPackets-1]
            utc = dt.datetime.utcnow()
            self.utcStr = utc.strftime("_%b%d_%H%M")
            ftype = '.bin'
            self.fname = self.dir + pktSel + self.utcStr + ftype

        # read recording length input and throw error if invalid
        try:
            recLen = float(self.recLen.get("1.0", "end-1c"))
            self.recLenInput = recLen
        except ValueError:
            self.errLab['text'] = "Invalid recording length!"
            self.errLab['fg'] = "#e00"
            return 1

        # read recording length input and throw error if invalid
        try:
            self.fileSizeCap = float(self.fs.get("1.0", "end-1c"))
        except ValueError:
            self.errLab['text'] = "Invalid filesize length!"
            self.errLab['fg'] = "#e00"
            return 1


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
            if self.result == 'start_rec':
                print("Acknowledging button press... beginning recording")
                errFlag = self.assertParameters()

                # if an error was thrown when assigning parameters, return to polling queue
                if errFlag:
                    self.queue.task_done()
                    self.checkQueue()
                    return

                # Write to logger file
                self.writeLog()

                # Destroy current window, spawn stream-record window from rxContinuous.py
                self.queue.task_done()
                self.destroy()
                sfr(self.rx_rate,
                    self.fname,
                    self.fc,
                    self.rx_gain,
                    self.offset_freq,
                    self.fileSizeCap,
                    self.recLenInput)
            else:
                # "catch" unknown queue elements.
                print('unknown item in queue...')

    def writeLog(self):
        # Open/create text file for logging
        with open(self.dir + 'rxLog.txt', 'a') as f:
            # fairly jank MAC address reformatting
            macFormat = [':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff) for ele in range(0, 8 * 6, 8)][::-1])]
            macString = ''.join(macFormat)
            f.write('\n')
            f.write('==================================================\n')
            row = "New recording started at " + self.utcStr[1:] + " from machine with MAC of " + macString + ".\n"
            f.write(row)
            row = "packet number: " + self.clicked.get() + ". \nfc = " + str(self.fc) + "Hz\n"
            f.write(row)
            row = "f_offset = " + str(self.offset_freq) + " Hz\n"
            f.write(row)
            row = "filename for this sequence begins with: " + self.fname[0:6] + ">" + self.fname[7:-4] + "_0" + self.fname[-4:] + "\n"
            f.write(row)
            row = "filesize cap: " + str(self.fileSizeCap) + " MB\n"
            f.write(row)
            row = "Recording time limit: " + str(self.recLenInput) + " min\n"
            f.write(row)
            f.write('==================================================\n')



# If we run this file as the main script...
if __name__=="__main__":
    k = ezRxWindow()


