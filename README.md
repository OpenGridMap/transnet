# Transnet
The Transnet project consists of a set of Python and Matlab scripts for the automatic inference of high voltage power (transmission) grids based on crowdsourced OpenStreetMap (OSM) data. Transnet yields two different models, a Common Information Model (CIM) model and a Matlab Simulink model. The latter can be used to perform load flow analysis. This manual guides you to the Transnet setup and gives several usage examples.

## Data Preparation
Download OSM data (.pbf) from https://download.geofabrik.de/ for the considered region, e.g. for Europe or Germany. Also download the corresponding shape file (.poly).

Install the osmosis tool, which is capable of filtering OSM data by (power) tags:
```
sudo apt-get install osmosis
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
  completeRelations=yes \
  --write-pbf file=’Downloads/power_extract1.pbf’
```

## PostgreSQL + PostGIS setup
Transnet relies on a local PostgreSQL + PostGIS installation, which is the host of power-relevant OSM data.
To install PostgreSQL + PostGIS open a terminal and execute the following command:
```
sudo apt-get install postgresql postgis
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
Install osm2pgsql tool for OSM data import:
```
sudo apt-get install osm2psql
```
