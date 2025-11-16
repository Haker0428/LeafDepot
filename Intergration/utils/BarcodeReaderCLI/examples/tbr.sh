#!/bin/bash

HERE="$(dirname "$(readlink -f "${0}")")"
cd $HERE

EXE=../bin/BarcodeReaderCLI
OUTDIR=/tmp/brcli
INPDIR=./images

# ===== Read barcode with TBR
$EXE $OPT $AUTH -type=datamatrix -tbr=120 -fields=+tbr "$INPDIR/dm.tbr.bmp"

