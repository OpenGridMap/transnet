# Transnet
The Transnet project consists of a set of Python and Matlab scripts for the automatic inference of high voltage power (transmission) grids based on crowdsourced OpenStreetMap (OSM) data. Transnet yields two different models, a Common Information Model (CIM) model and a Matlab Simulink model. The latter can be used to perform load flow analysis. This manual guides you to the Transnet setup and gives several usage examples.

## Environment Details
|System/Application/Tool|Version|Description|
|---|---|---|
|Ubuntu|12.04|Linux distribution|
|PostgreSQL|9.4|PostgreSQL Database server|
|PostGIS|9.2|PostgreSQL GIS extension|
|osmosis|0.44.1-2|OSM data filtering/merging tool|
|osm2pgsql|0.88.1-1|OSM data import-into-PostgreSQL tool|
|Python|2.7||
|Shapely|1.5.13|Python module for GIS operations|
|Psycopg2|2.6.1|Python module for PostgreSQL support|
|PyCIM|15.13.4|Python module for CIM modeling|

## Setup Transnet Project:
Transnet requires Python-2.7, which can be installed as follows:
```
sudo apt-get install python-2.7
```
Moreover, QGIS has to be installed - the installation guide for Linux systems can be found here:
http://qgis.org/en/site/forusers/alldownloads.html#linux

A few additional Python packages have to be installed:
```
sudo apt-get install python-psycopg2 python-shapely
easy_install PyCIM
```
Finally checkout the Transnet project:
```
git clone https://github.com/OpenGridMap/transnet transnet
```

## Data Preparation
Download OSM data (.pbf) from https://download.geofabrik.de/ for the considered region, e.g. for Europe or Germany. Also download the corresponding shape file (.poly).

Install the LATEST osmosis tool, which is capable of filtering OSM data by (power) tags:
```
mkdir osmosis && cd osmosis
wget http://bretth.dev.openstreetmap.org/osmosis-build/osmosis-latest.tgz
tar xvfz osmosis-latest.tgz
chmod +x bin/osmosis
```
Filter all nodes, ways and relations tagged with 'power=*':
```
osmosis \
  --read-pbf file=’Downloads/germany-latest.osm.pbf’ \
  --tag-filter accept-relations power=* \
  --tag-filter accept-ways power=* \
  --tag-filter accept-nodes power=* \
  --used-node --buffer \
  --bounding-polygon file=’Downloads/germany.poly’ \
  completeRelations=yes \
  --write-pbf file=’Downloads/power_extract1.pbf’
```
Filter all relations tagged with 'route=power':
```
osmosis \
  --read-pbf file=’Downloads/germany-latest.osm.pbf’ \
  --tag-filter accept-relations route=power \
  --used-way \
	--used-node \
  --buffer \
  --bounding-polygon file=’Downloads/germany.poly’ \
  completeRelations=yes completeWays=yes \
  --write-pbf file=’Downloads/power_extract2.pbf’
```
Get all power ways and its nodes (even if they are not power-tagged):
```
osmosis \
  --read-pbf file=’Downloads/germany-latest.osm.pbf’ \
  --tag-filter accept-ways power=* \
  --used-node --buffer \
  --bounding-polygon file=’Downloads/germany.poly’ \
  completeWays=yes \
  --write-pbf file=’Downloads/power_extract3.pbf’
```
Merge first 2 extracts:
```
osmosis \
--read-pbf file=’Downloads/power_extract1.pbf’\
--read-pbf file=’Downloads/power_extract2.pbf’\
--merge \
--write-pbf file=’Downloads/power_extract12.pbf’
```
Merge with 3rd extract:
```
osmosis \
--read-pbf file=’Downloads/power_extract12.pbf’\
--read-pbf file=’Downloads/power_extract3.pbf’\
--merge \
--write-pbf file=’Downloads/power_extract.pbf’
```

## PostgreSQL + PostGIS setup
Transnet relies on a local PostgreSQL + PostGIS installation, which is the host of power-relevant OSM data.
To install PostgreSQL + PostGIS open a terminal and execute the following command:
```
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt/ precise-pgdg main" >> /etc/apt/sources.list'
wget --quiet -O - http://apt.postgresql.org/pub/repos/apt/ACCC4CF8.asc | sudo apt-key add -
sudo apt-get update
sudo apt-get install postgresql-9.4-postgis pgadmin3 postgresql-contrib
```
Change password of user postgres:
```
sudo -u postgres psql -c '\password'
```
Create a PostGIS-enabled database template:
```
sudo -u postgres createdb -U postgres -h localhost transnet_template
sudo -u postgres psql -d transnet_template -U postgres -h localhost -f /usr/share/postgresql/9.1/contrib/postgis-1.5/postgis.sql
sudo -u postgres psql -d transnet_template -U postgres -h localhost -f /usr/share/postgresql/9.1/contrib/postgis-1.5/spatial_ref_sys.sql
sudo -u postgres psql -d transnet_template -U postgres -q -h localhost -c "CREATE EXTENSION hstore;"
```
Create a database using the template:
```
sudo -u postgres psql -U postgres -d transnet_template -h localhost -c "CREATE DATABASE power_de WITH TEMPLATE = transnet_template;"
```
## Data Import
The data import is performed with the tool osm2pgsql. To install the latest version, the boost library and a C/C++-Compiler are required. Here are some useful links to install these requirements:

Install boost library - http://stackoverflow.com/questions/12578499/how-to-install-boost-on-ubuntu
Install C/C++ Compiler - http://askubuntu.com/questions/466651/how-do-i-use-the-latest-gcc-on-ubuntu-14-04
Setup C/C++ Compiler - http://askubuntu.com/questions/26498/choose-gcc-and-g-version

Install the LATEST osm2pgsql tool for OSM data import:
```
git clone https://github.com/openstreetmap/osm2pgsql osm2pgsql
sudo apt-get install make cmake g++ libboost-dev libboost-system-dev \
  libboost-filesystem-dev libexpat1-dev zlib1g-dev \
  libbz2-dev libpq-dev libgeos-dev libgeos++-dev libproj-dev lua5.2 \
  liblua5.2-dev
cd osm2pgsql && mkdir build && cd build
cmake ..
make
sudo make install
```
Import data extract from above into database:
```
osm2pgsql -r pbf --username='postgres' -d power_de -k -s -C 6000 -v --host='localhost' --port='5432' --password --style transnet/util/power.style Downloads/power_extract.pbf
```
