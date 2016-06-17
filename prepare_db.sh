#!/bin/sh

data_dump=/Users/lej/Downloads/japan-latest.osm.pbf

# load the appropriate config file
source 'configs/bayern.conf'

# create new database
psql -U $duser -d transnet_template -h localhost -c "CREATE DATABASE $dname WITH TEMPLATE = transnet_template;"

# filter all power nodes/ways of relations tagged with "power=*"
osmosis --read-pbf file=$data_dump --tag-filter accept-relations power=* --tag-filter accept-ways power=* --tag-filter accept-nodes power=* --used-node --buffer --bounding-polygon file=$pfile completeRelations=yes --write-pbf file="data/$destdir/power_extract1.pbf"

# filter all relations tagged with "route=power"
osmosis --read-pbf file=$data_dump --tag-filter accept-relations route=power --used-way --used-node --buffer --bounding-polygon file=$pfile completeRelations=yes completeWays=yes --write-pbf file="data/$destdir/power_extract2.pbf"

# filter all ways and its corresponding nodes tagged with "power=*"
osmosis --read-pbf file=$data_dump --tag-filter accept-ways power=* --used-node --buffer --bounding-polygon file=$pfile completeWays=yes --write-pbf file="data/$destdir/power_extract3.pbf"

# merge all extracts
osmosis --read-pbf file="data/$destdir/power_extract1.pbf" --read-pbf file="data/$destdir/power_extract2.pbf" --merge --write-pbf file="data/$destdir/power_extract12.pbf"
osmosis --read-pbf file="data/$destdir/power_extract12.pbf" --read-pbf file="data/$destdir/power_extract3.pbf" --merge --write-pbf file="data/$destdir/power_extract.pbf"

# import to postgresql database
osm2pgsql -r pbf --username=$duser -d $dname -k -s -C 6000 -v --host='localhost' --port='5432' --password --style util/power.style "data/$destdir/power_extract.pbf"
