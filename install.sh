#!/usr/bin/env bash

# Begin with checking for and installing UHD python library
hasuhd=$(find /usr/local/lib/python3/dist-packages/python/ -maxdepth 1 -type d -name "uhd")

if [[ -z "$hasuhd" ]]; then
  echo "No UHD found! Proceeding with install."

  # --- proceed with UHD install ---
  uhdInstallDir=$(pwd)
  uhdInstallDir+="/sh/installUHD.sh"
  source uhdInstallDir

elif [[ -n "$hasuhd" ]]; then
  echo "UHD library located in $hasuhd"
fi
