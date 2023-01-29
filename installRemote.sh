#!/usr/bin/env bash

# === Begin with checking for and installing UHD python library ===
#hasUhd=$(find /usr/local/lib/ -mindepth 1 -type d -name "uhd" | head -1)
hasUhd=$(find /usr/local/lib/ -type d -name "python3*" -exec find {} -name "uhd" \; | head -1)
echo "found uhd on path $hasUhd"

#if [[ -z "$hasuhd" ]] && [[ -z "$hasUhd2" ]]; then
if [[ -z "$hasUhd" ]]; then
  echo "No UHD found! Proceeding with install."

  # --- proceed with UHD install ---
  uhdInstallDir=$(pwd)
  uhdInstallDir+="/sh/installUHD.sh"
  source $uhdInstallDir
  
  # locate installed UHD library
  hasuhd=$(find /usr/local/lib/python3/dist-packages/ -maxdepth 2 -type d -name "uhd")
  hasUhd2=$(find /usr/local/lib/python3.8/ -maxdepth 2 -type d -name "uhd")
fi

# --- jot down name of directory w/ uhd to var "uhdDir"
if [[ -n "$hasUhd" ]]; then
  echo "UHD library located in $hasuhd"
  uhdDir="$hasUhd"
fi

# === Copy and install relevant Tx/Rx scripts ===
git clone "https://github.com/brandonthunt/pyOta.git"
yes | rm -r "pyOta/.git"
cpfDir=$(pwd)
cpfDir+="/sh/copyFiles.sh"
source $cpfDir



# Rx
#gio set ~/Desktop/universalRx.desktop metadata::trust true
chmod a+x "$HOME/Desktop/universalRx.desktop"
gio set ~/Desktop/universalRx.desktop metadata::trust true


# === Generate launcher shell scripts === 
# Tx launcher
touch "$HOME/Software/pyOta/launchTx.sh"
uhdParentDir="$(dirname "$uhdDir")"
echo "#!/usr/bin/env bash
PYTHONPATH=$uhdParentDir python3 ezTx.py" > "$HOME/Software/pyOta/launchTx.sh"
chmod +x "$HOME/Software/pyOta/launchTx.sh"

# Rx launcher
touch "$HOME/Software/pyOta/launchRx.sh"
uhdParentDir="$(dirname "$uhdDir")"
echo "#!/usr/bin/env bash
PYTHONPATH=$uhdParentDir python3 ezRx.py" > "$HOME/Software/pyOta/launchRx.sh"
chmod +x "$HOME/Software/pyOta/launchRx.sh"

if [[ -n $(find "$HOME" -maxdepth 1 -type d -name ".tempInstallDir") ]]; then
  yes | rm -r "$HOME/.tempInstallDir"
fi


