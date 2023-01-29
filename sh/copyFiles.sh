#!/usr/bin/env bash
# Copy files to software directory

# --- If "Software" folder does not exist, create it ---
hasDir=$(find $HOME -maxdepth 1 -type d -name "Software")

if [[ -z "$hasDir" ]]; then
  mkdir "$HOME/Software"
fi

# --- Check for old installs, remove if found ---
dirExist=$(find "$HOME/Software" -maxdepth 1 -type d -name "ezTrx")
if [[ -n $dirExist ]]; then
  echo "Found old install, replacing with current verison."
  rm -r "$HOME/Software/ezTrx"
fi

dirExist=$(find "$HOME/Software" -maxdepth 1 -type d -name "pyOta")
if [[ -n $dirExist ]]; then
  echo "Found old install, replacing with current verison."
  rm -r "$HOME/Software/pyOta"
fi

#mkdir "$HOME/Software/ezTrx"
yes | cp -r "$(pwd)/pyOta/" "$HOME/Software"
yes | rm -r pyOta
cd $HOME/Software/pyOta
dirName="${PWD}"
mkdir rxBins

# --- Create .desktop files ---
# generate Tx desktop file
touch "$HOME/Desktop/universalTx.desktop"
echo "[Desktop Entry]
Path=$dirName
Version=1.0
Name=UniversalTx
Comment=Transmit any waveform contained in a .bin file
Exec=$dirName/launchTx.sh
Terminal=false
Type=Application
Icon=$dirName/icon.png
StartupNotify=true
Hidden=false
#NoDisplay=false" > "$HOME/Desktop/universalTx.desktop"

# Set permissions to allow executable
chmod a+x "$HOME/Desktop/universalTx.desktop"
gio set $HOME/Desktop/universalTx.desktop metadata::trust false
gio set $HOME/Desktop/universalTx.desktop metadata::trust true


# generate Rx desktop file
touch "$HOME/Desktop/universalRx.desktop"
echo "[Desktop Entry]
Path=$dirName
Version=1.0
Name=UniversalRx
Comment=Receive and record data in a 1MHz bandwidth to a *.bin file.
Exec=$dirName/launchRx.sh
Terminal=false
Type=Application
Icon=$dirName/icon.png
StartupNotify=true
Hidden=false
#NoDisplay=false" > "$HOME/Desktop/universalRx.desktop"

# Set permissions to allow executable
chmod a+x "$HOME/Desktop/universalRx.desktop"
gio set $HOME/Desktop/universalTx.desktop metadata::trust false
gio set $HOME/Desktop/universalRx.desktop metadata::trust true

