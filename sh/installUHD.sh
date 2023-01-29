#!/usr/bin/env bash
# Update dependencies (follows Ettus' recommendation)
sudo apt-get install libboost-all-dev libusb-1.0-dev python-mako doxygen python-docutils cmake build-essential

# clone git repo
currDir=$(pwd)
mkdir ~/.tempInstallDir
cd ~/.tempInstallDir
git clone https://github.com/EttusResearch/uhd.git
cd uhd/host
mkdir build
cd build
cmake -DENABLE_TESTS=OFF -DENABLE_C_API=OFF -DENABLE_MANUAL=OFF -B/usr/local/lib/python3/dist-packages -S/$(pwd)
sudo make -j8
export DESTDIR="/usr/local/lib/python3"sudo make install
sudo ldconfig
cd $currDir
