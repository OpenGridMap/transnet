#!/bin/bash
# launch a complete Transnet run

if [ "$#" -ne 0 ]; then
  # load the appropriate config file
  source "$1"
fi

mkdir -p "../logs/$destdir"

# matlab directory epezhman
matlab='/usr/local/bin/matlab'

# matlab directory remote
#matlab='/usr/bin/matlab'

# run transnet
cdir=`pwd`
cd ../app

if [ "$#" -eq 2 ]; then
    mkdir -p "../logs/planet/$destdir"
    python Transnet.py -c $continent -m $matlab -g | tee "../logs/planet/$destdir/transnet.log"
else
    python Transnet.py -c $continent -m $matlab | tee "../logs/$destdir/transnet.log"
fi

cd $cdir

