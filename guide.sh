#!/bin/bash
# launch a complete Transnet run

# select continent
wget -qO- "http://download.geofabrik.de" | grep '<td class="subregion"' | sed -E 's/.*<a href="\.\/([-a-z]*)\.html.*<\/a><\/td>/\1/g'
echo 'Please enter the high-level region you want to do the inference for:'
read continent

# select country
wget -qO- "http://download.geofabrik.de/$continent.html" | grep -e '<tr onMouseOver=.*<td class="subregion"' | sed -E 's/.*<a href="([-a-z]*\/)?([-a-z]*).html">([-A-Za-z \(\)\,]*)<\/a><\/td>/\2 (\3)/g'
echo 'Please enter the region you want to do the inference for:'
read country

export ddump_url="http://download.geofabrik.de/$continent/$country-latest.osm.pbf"
export pfile_url="http://download.geofabrik.de/$continent/$country.poly"
export dname="$country"
export destdir="$country"

echo "Please specify the voltage levels in Volts you want to do the inference for, e.g. '220000|380000'"
read vlevels
export vlevels="$vlevels"

echo "Finally, please specify the list of arguments \(a list of space-separated options, e.g. '-t -v'\) for the Transnet inference:"
echo '-t ... plot topology'
echo '-v ... verbose logging'
echo '-l ... load estimation (does only work for Germany, Austria and Switzerland)'
echo '-e ... evaluation of point-to-point connections \(only makes sense for Germany, since coverage of OSM data is sufficient high\)'
read trans_args
export trans_args="$trans_args"

echo 'Please enter the database user:'
read duser
export duser="$duser"
echo 'Please enter the database password:'
read dpassword
export dpassword="$dpassword"
export PGPASS="$dpassword"

sh prepare_db.sh
sh run.sh
