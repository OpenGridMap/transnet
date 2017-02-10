#!/bin/bash

if [ "$#" -ne 0 ]; then
  # load the appropriate config file
  source "$1"
fi

mkdir -p "../data/$destdir"

if [ ! -z ${ddump_url+x} ]
  then
        echo "Downloading $ddump_url"
        wget "$ddump_url" -O "../data/$destdir/ddump.pbf"
        ddump="../data/$destdir/ddump.pbf"
  else
	echo "Using dump file $ddump"
fi

if [ ! -z ${pfile_url+x} ]
  then
        echo "Downloading $pfile_url"
        wget "$pfile_url" -O "../data/$destdir/pfile.poly"
        pfile="../data/$destdir/pfile.poly"
  else
	echo "Using poly file $pfile"
fi

echo "1. Drop the database"
psql -U $duser -h localhost -c "DROP DATABASE $dname;"

echo "2. create new database"
psql -U $duser -d transnet_template -h localhost -c "CREATE DATABASE $dname WITH TEMPLATE = transnet_template;"

echo "3. filter all power nodes/ways of relations tagged with power=*"
osmosis --read-pbf file="$ddump" --tag-filter accept-relations power=* --tag-filter accept-ways power=* --tag-filter accept-nodes power=* --used-node --buffer --bounding-polygon file="$pfile" completeRelations=yes --write-pbf file="../data/$destdir/power_extract1.pbf"

echo "4. filter all relations tagged with route=power"
osmosis --read-pbf file="$ddump" --tag-filter accept-relations route=power --used-way --used-node --buffer --bounding-polygon file="$pfile" completeRelations=yes completeWays=yes --write-pbf file="../data/$destdir/power_extract2.pbf"

echo "5. filter all ways and its corresponding nodes tagged with power=*"
osmosis --read-pbf file="$ddump" --tag-filter accept-ways power=* --used-node --buffer --bounding-polygon file="$pfile" completeWays=yes --write-pbf file="../data/$destdir/power_extract3.pbf"

echo "6. merge all extracts"
osmosis --read-pbf file="../data/$destdir/power_extract1.pbf" --read-pbf file="../data/$destdir/power_extract2.pbf" --merge --write-pbf file="../data/$destdir/power_extract12.pbf"
osmosis --read-pbf file="../data/$destdir/power_extract12.pbf" --read-pbf file="../data/$destdir/power_extract3.pbf" --merge --write-pbf file="../data/$destdir/power_extract.pbf"

echo "7. import to postgresql database"
osm2pgsql -r pbf --username=$duser -d $dname -E 3857 -k -s -C 6000 -v --host='localhost' --port='5432' --style ../util/power.style "../data/$destdir/power_extract.pbf"
