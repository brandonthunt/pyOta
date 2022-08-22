from rxContinuous import streamFromRadio as sfr
import numpy as np
import datetime as dt
import queue
import tkinter as tk
from threading import *

class ezRxWindow(tk.Tk):
    # --- attributes ---
    # empty list for streamed samples
    rx_gain = 8
    offset_freq = 100000
    rx_rate = 1000000

    def __init__(self, fname, fc):
        # create tkinter window
        super().__init__()
        self.geometry("200x400")

        # initialize Queue and begin polling
        self.queue = queue.Queue()
        self.after(100, self.checkQueue)

        # copy/include parameters
        self.fc = fc + self.offset_freq
        self.fname = fname

        """ GUI/HMI Interactivity Construction """
        # create fc and textbox
        self.lab = tk.Label(self, text="Center Frequency [kHz]:")
        self.lab.pack()
        self.fcbox = tk.Text(self, height=1, width=20, pady=1)
        self.fcbox.pack(pady=5)

        # create fname label and dropdown
        self.droplab = tk.Label(self, text="Packet number: ")
        self.droplab.pack(pady=1)
        clicked = tk.StringVar()
        clicked.set("Click to select")                                # default string
        nPackets = 10                                                 # number of packet options to support
        options = ["Packet " + str(i) for i in range(nPackets)]       # packet selection options
        self.drop = tk.OptionMenu(self, clicked, *options)
        self.drop.pack()

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
            return 0
        except ValueError:
            self.errLab['text'] = "Invalid center freq.!"
            self.errLab['fg'] = "#e00"
            return 1

        # read fname dropdown


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

                # if an error was thrown, return to polling queue
                if errFlag:
                    self.queue.task_done()
                    self.checkQueue()
                    return

                print("TODO: COPY SELF PARAMS BEFORE LAUNCH")
                self.destroy()
                sfr(self.rx_rate,
                    self.fname,
                    self.fc,
                    self.rx_gain,
                    self.offset_freq)

                self.queue.task_done()

            else:
                # "catch" unknown queue elements.
                print('unknown item in queue...')


# If we run this file as the main script...
if __name__=="__main__":
    k = ezRxWindow('rxBins/test.bin', 6116000)


