#!/bin/bash

HERE="$(dirname "$(readlink -f "${0}")")"
cd $HERE

EXE=../bin/BarcodeReaderCLI
OUTDIR=/tmp/brcli
rm -rf $OUTDIR
INPDIR=./images

# ===== Use configuration file to setup complex processing. Demonstrates:
$EXE $OPT $AUTH @"brcli-example.config"

