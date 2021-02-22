#!/bin/bash -f

command -v python || (
    apt-get update
    apt-get install -y python
)

cd "$(dirname "$0")/.." || exit $?

rm -rf build
mkdir build
cd build

cmake .. && make
