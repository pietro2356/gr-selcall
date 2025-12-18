#! /bin/bash

# Remove any existing build directory
rm -rf ./build
mkdir ./build
cd ./build

# Configure the build with a custom installation prefix
cmake -DCMAKE_INSTALL_PREFIX=/home/ngn/.grc_gnuradio/ ..
make
make install

# Ensure the local Python path is included in PYTHONPATH
if [[ ":$PYTHONPATH:" == *":/home/ngn/.grc_gnuradio/lib/python3.10/site-packages/:"* ]]; then
  echo "Local path is correctly set in 'PYTHONPATH'"
else
  echo "Local path is missing in 'PYTHONPATH', adding it now."
  echo "export PYTHONPATH=$PYTHONPATH:/home/ngn/.grc_gnuradio/lib/python3.10/site-packages/" >> ~/.bashrc
  source ~/.bashrc
  echo "Local path added to 'PYTHONPATH' via ~/.bashrc"
fi