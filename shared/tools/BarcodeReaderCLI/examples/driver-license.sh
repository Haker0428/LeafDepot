#!/bin/bash

HERE="$(dirname "$(readlink -f "${0}")")"
cd $HERE

EXE=../bin/BarcodeReaderCLI
OUTDIR=/tmp/brcli
INPDIR=./images

# ===== Read and decode Driver License
$EXE $OPT $AUTH -type=drvlic "$INPDIR/test.tif"


