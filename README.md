# pyOta
OTA recodring scripts for use with Ettus USRPs (requires UHD python module)

~ Running scripts ~
1) Open a terminal window and navigate to the directory containing the scripts
2) enter "python3 <script name>.py [arguments]
    e.g., to record with center freq 6116kHz and name file "test.bin", enter: python3 rxContinuous.py -f 6116000 -n "test.bin"
    The saved file will be in the rxBins subdirectory. To transmit a specific file, that file must be in the txBins/ subdir. 
3) When finished, close the Tk window using the button. The transmission is then either ended or the file is saved. 

~ Scripts ~
txContinuous.py
rxContinuous.py

To view all script arguments, type "python3 <script name>.py --help"
Typically, only the carrier frequency [-f] and filename [-n] should be specified. Default values for other arguments are suitable. 
  
