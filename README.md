# Transnet
The Transnet project consists of a set of Python and Matlab scripts for the automatic inference of high voltage power (transmission) grids based on crowdsourced OpenStreetMap (OSM) data. Transnet yields two different models, a Common Information Model (CIM) model and a Matlab Simulink model. The latter can be used to perform load flow analysis. This manual guides you to the Transnet setup and gives several usage examples.

## Setup Transnet Project (Ubuntu 16.04):
Checkout the Transnet project:
```
git clone https://github.com/OpenGridMap/transnet transnet
```
### Setup Python With Conda
Download and install miniconda for Python-2.7 (http://conda.pydata.org/miniconda.html)
```
# dismiss yes/no installation dialogs
conda config --set always_yes true
# create transnet environment and install shapely package
conda create --name transnet shapely
# change to transnet environment
source activate transnet
# install required python packages
conda install --channel https://conda.anaconda.org/IOOS cartopy
conda install psycopg2
conda install -c auto PyCIM
conda install scipy
conda install -c anaconda mysql-connector-python=2.0.3
conda install matplotlib
conda install gdal
```

### Database Setup
## PostgreSQL + PostGIS setup
Transnet relies on a local PostgreSQL + PostGIS installation, which is the host of power-relevant OSM data.
To install PostgreSQL + PostGIS open a terminal and install the tool _osm2pgsql_, which should also install the required PostgreSQL + PostGIS database:
```
sudo apt-get install osm2pgsql
```
Change password of user postgres:
```
sudo -u postgres psql -c '\password'
```
Create a PostGIS-enabled database template:
```
sudo -u postgres createdb -U postgres -h localhost transnet_template
sudo -u postgres psql -d transnet_template -U postgres -q -h localhost -c "CREATE EXTENSION postgis;"
sudo -u postgres psql -d transnet_template -U postgres -q -h localhost -c "CREATE EXTENSION hstore;"
sudo -u postgres psql -d transnet_template -U postgres -h localhost -f transnet/sql/transnet_functions.sql
```
## Data Preparation
The data is filtered for power-relevant data by the _osmosis_ tool and the import to the PostgreSQL database is done with the _osm2pgsql_ tool.
Install the tool _osmosis_:
```
sudo apt-get install osmosis
```
Now you are ready to go to use the _prepare_db.sh_ shell script that sets up the database for a specific region for you.
The script requires the path to a config file as input parameter. For several countries such config files already exist in the _configs_ subdirectory.
For example, let's have a look at the config file for Austria (_configs/austria.conf_):
```
### Database
dname='austria'
duser='postgres'
dpassword='OpenGridMap'

### Data Source and Destination
## Data Source
# specify either the location of dump and poly file or specify the download link
#ddump=/Users/lej/Downloads/austria-latest.osm.pbf
#pfile='/Users/lej/Downloads/austria.poly'
ddump_url='http://download.geofabrik.de/europe/austria-latest.osm.pbf'
pfile_url='http://download.geofabrik.de/europe/austria.poly'
## Destination Directory
destdir='austria'

### Transnet
vlevels='220000|380000'
## Transnet arguments
# -t plot topology
# -v verbose logging
# -l load estimation (does only work for Germany, Austria and Switzerland)
# -e evaluation of point-to-point connections (only makes sense for Germany, since coverage of OSM data is sufficient high)
trans_args='-t'
```
As you can see, the config file requires you to specify the database name, user, and password for the database.
Furthermore, you can decide whether to specify the download links to the OSM data dump file and the corresponding poly (region boundary) file or to specify the path to the already downloaded files.
Finally, for the execution of Transnet (later on) you can choose from various arguments, as described in the config file.

Once the config file is ready, prepare the database with the following command:
```
cd transnet
./prepare_db.sh configs/austria.conf
```
Note: The execution will request you for the database password once again. If you want to disable such requests, specify a .passfile in your home directory according to https://www.postgresql.org/docs/9.1/static/libpq-pgpass.html.

## MySQL Database
The administrative data for the load estimation is derived from OpenGeoDB. To provide OpenGeoDB locally, we set up a local MySQL database and import an OpenGeoDB dump.
```
sudo apt-get install mysql
TBC
```

### Run Transnet
Once you have set up the database, you are ready to go to run Transnet with the _run.sh_ script. Before that, make sure that you have configured the right path to your MATLAB installation in _run.sh_.
To run Transnet for a specific region (in this case Austria), enter the following command:
```
./run.sh configs/austria.conf
```
After a successful inference the resulting models are placed into the _models/$destdir_ subdirectory. 
