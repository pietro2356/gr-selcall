#! /bin/bash

rm -rf ./build
mkdir ./build
cd ./build

cmake -DCMAKE_INSTALL_PREFIX=/home/ngn/.grc_gnuradio/ ..
make
make install