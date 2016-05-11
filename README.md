# Transnet
The Transnet project consists of a set of Python and Matlab scripts for the automatic inference of high voltage power (transmission) grids based on crowdsourced OpenStreetMap (OSM) data. Transnet yields two different models, a Common Information Model (CIM) model and a Matlab Simulink model. The latter can be used to perform load flow analysis. This manual guides you to the Transnet setup and gives several usage examples.

## PostgreSQL + PostGIS setup
Transnet relies on a local PostgreSQL + PostGIS installation, which is the host of power-relevant OSM data.
To install PostgreSQL + PostGIS open a terminal and execute the following command:
```
echo "deb http://apt.postgresql.org/pub/repos/apt/ precise-pgdg main" | sudo tee /etc/apt/sources.list.d/postgis.list
wget --quiet -O - http://apt.postgresql.org/pub/repos/apt/ACCC4CF8.asc | sudo apt-key add -
sudo apt-get update
sudo apt-get install postgresql-9.3 postgresql-9.3-postgis-2.1 postgresql-client-9.3
sudo -u postgres psql -c '\password'
sudo -u postgres psql -c 'create extension postgis;'
```
Create a PostGIS-enabled database template:
```
sudo -u postgres createdb -U postgres -h localhost plpgsql transnet_template
```
