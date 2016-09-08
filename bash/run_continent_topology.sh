#!/bin/bash
# launch a complete Transnet run

if [ "$#" -ne 0 ]; then
  # load the appropriate config file
  source "$1"
fi

mkdir -p "../logs/$destdir"

# run transnet
cdir=`pwd`
cd ../app

if [ "$#" -eq 2 ]; then
    mkdir -p "../logs/planet/$destdir"
    python Transnet.py -c $continent -D $dname -U $duser -X $dpassword $trans_args -g | tee "../logs/planet/$destdir/transnet.log"
else
    python Transnet.py -c $continent -D $dname -U $duser -X $dpassword $trans_args | tee "../logs/$destdir/transnet.log"
fi

cd $cdir

