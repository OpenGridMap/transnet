#!/bin/bash
# launch a complete Transnet run

# configure the right matlab binary direction
matlab='/usr/local/bin/matlab'

if [ "$#" -ne 0 ]; then
  # load the appropriate config file
  source "$1"
fi

mkdir -p "logs/$destdir"

# run transnet
cdir=`pwd`
cd app
python Transnet.py -c $continent -D $dname -U $duser -X $dpassword $trans_args | tee "../logs/$destdir/transnet.log"
cd $cdir

