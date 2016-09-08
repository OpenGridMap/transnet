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
    date > mm.txt
    python Transnet.py -c $continent -D $dname -U $duser -X $dpassword -j -g | tee "../logs/$destdir/transnet.log"
else
    date > nn.txt
    python Transnet.py -c $continent -D $dname -U $duser -X $dpassword -j | tee "../logs/$destdir/transnet.log"
fi

cd $cdir

