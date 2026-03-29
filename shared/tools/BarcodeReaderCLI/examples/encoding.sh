#!/bin/bash

HERE="$(dirname "$(readlink -f "${0}")")"
cd $HERE

EXE=../bin/BarcodeReaderCLI
OUTDIR=/tmp/brcli
rm -rf $OUTDIR
mkdir $OUTDIR
INPDIR=./images

# ===== Use configuration file to setup complex processing. Demonstrates:
#   - Reading files with language-specfic file names
#   - Reading language-specfic barcode test values
#   - Template-based format of TXT output 

# ==== To recognize UTF8 filenames in test/images/encoding folder, system locale should be set to UTF-8
#  For example  starting Docker Ubuntu container call:
#     RUN apt update && apt-get install -y locales-all
#     ENV LC_ALL en_US.UTF-8

$EXE $OPT $AUTH -d="OUTDIR=$OUTDIR/" @"encoding.config" -output=console

echo Output is written to $OUTDIR folder:
ls $OUTDIR

