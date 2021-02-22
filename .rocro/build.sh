#!/bin/bash -f

cd "$(dirname "$0")/.." || exit $?

rm -rf build
mkdir build
cd build

cmake .. && make
