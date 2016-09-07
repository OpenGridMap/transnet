#!/bin/bash
# launch a complete Transnet run

if [ "$#" -ne 0 ]; then
  # load the appropriate config file
  source "$1"
fi

mkdir -p "../logs/$destdir"

# configure the right matlab binary direction
matlab='/usr/bin/matlab'

# run transnet
cdir=`pwd`
cd ../app
python Transnet.py -c $continent -m $matlab | tee "../logs/$destdir/transnet.log"
cd $cdir

