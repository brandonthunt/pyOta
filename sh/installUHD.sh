#!/usr/bin/env bash
# Update dependencies (follows Ettus' recommendation)
sudo apt-get install libboost-all-dev libusb-1.0-dev python-mako doxygen python-docutils cmake build-essential

# clone git repo
mkdir ~/.tempInstallDir
cd ~/.tempInstallDir
git clone git://github.com/EttusResearch/uhd.git
cd uhd/host
mkdir build
cd build
cmake -DENABLE_TESTS=OFF -DENABLE_C_API=OFF -DENABLE_MANUAL=OFF ..
make -j8
sudo make install
sudo ldconfig