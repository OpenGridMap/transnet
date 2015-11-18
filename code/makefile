###################################################################################
#									          #
#	Copyright "2015" "NEXT ENERGY"						  #
#										  #
#	Licensed under the Apache License, Version 2.0 (the "License");		  #
#	you may not use this file except in compliance with the License.	  #
#	You may obtain a copy of the License at					  #
#										  #
#	    http://www.apache.org/licenses/LICENSE-2.0				  # 
#										  #	
#	Unless required by applicable law or agreed to in writing, software	  #
#	distributed under the License is distributed on an "AS IS" BASIS,	  #
#	WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  #
#	See the License for the specific language governing permissions and	  #
#	limitations under the License.						  #	
#										  #
###################################################################################


# This makefile executes the following tasks:

# Step0. 
#	 Filter the raw planet OSM data spatially and thematically.	

# IMPORTANT: Note that this step is **commented out** here. As the OSM planet file has a quite big size, 
# it is not possible to provide it with the SciGRID model folder. 
# However, the user can download the OSM planet file and **uncomment** this step and filter the data for the "power" tag. 

# Step1.
#	 Create the postgis template database with the hstore extension.

# Step2. 
#        Create an empty database using the postgis and hstore extensions created in step1. 

# Step3. 
#	Export the OSM filtered power data filtered in step0 using osm2pgsql to the database created in Step2. 
       
# Step4. 
#	Execute the abstraction script on the database created in Step2 to obtain the abstracted transmission network.


# Step5. Stores the vertices and links of the abstracted network to a .csv file. 


			###########    IMPORTANT   ##############


# Before running the makefile check the following:

# 1. Make sure that you already installed postgresql, osmosis and osm2pgSQL on your system.

# 2. Make sure that the different paths which are set in the section 'Environment Varibles Setting' in this makefile are set correctly. 
#    The paths are based on the folder sturcture delivered with the SciGRID code. 
#    Change the paths according to where the data, the tools and software used are located on your system if you chose to adopt another folder structure.

# 3. Define the different files paths, files names and database names following in the config.txt file:
 
# 4. Make sure that the names of the databases provided in the config.txt are unique, i.e.
#    there are no databases with the same names which already exist. Otherwise the makefile will exit with an error.



#==============================================================================#
# 		     Databases and power data folder names	               #	
#==============================================================================# 

# Database name (to be set in the config.txt file)
db_name:=$(shell grep -o 'db_name=[^\]*' config.txt | cut -f2- -d'=')
# Name of the OSM raw data file (to be set in the config.txt file)
OSM_raw:=$(shell grep -o 'OSM_raw=[^\]*' config.txt | cut -f2- -d'=')
OSM_power_extract1:=$(shell grep -o 'OSM_power_extract1=[^\]*' config.txt | cut -f2- -d'=')
OSM_power_extract2:=$(shell grep -o 'OSM_power_extract2=[^\]*' config.txt | cut -f2- -d'=')
OSM_power_all:=$(shell grep -o 'OSM_power_all=[^\]*' config.txt | cut -f2- -d'=')


#==============================================================================#
# 			    Style file and tools location	               #	
#==============================================================================# 

# Name of the stylefile (to be set in the config.txt file)
stylefile_name := $(shell grep -o 'stylefile_name=[^\]*' config.txt | cut -f2- -d'=')
# Name of the postgis database (to be set in the config.txt file)
postgis_name := $(shell grep -o 'postgis_name=[^\]*' config.txt | cut -f2- -d'=')
# Location of the Osmosis binary executable.
osmosis_folder := $(shell grep  -o 'osmosis_folder=[^\]*' config.txt | cut -f2- -d'=')
# Location of Osm2pgSQL
osm2pgsql_folder := $(shell grep  -o 'osm2pgsql_folder=[^\]*' config.txt | cut -f2- -d'=')
# postgis.sql and spatial_ref_sys.sql files location:
postgis_folder := $(shell grep  -o 'postgis_folder=[^\]*' config.txt | cut -f2- -d'=')


#==============================================================================#
#                 Environment varibles setting (folder paths)		       #
#==============================================================================#
    # The paths indicated here are relative to the folder SciGRID/code/scripts

# OSM raw data folder:
osm_raw_data:=$(shell grep  -o 'osm_raw_data=[^\]*' config.txt | cut -f2- -d'=')
# OSM raw power data folder:
osm_raw_power_data:=$(shell grep  -o 'osm_raw_power_data=[^\]*' config.txt | cut -f2- -d'=')
# Abstraction folder:
abstraction_folder:=$(shell grep  -o 'abstraction_folder=[^\]*' config.txt | cut -f2- -d'=')
# Network (output) folder:
network:=$(shell grep  -o 'network=[^\]*' config.txt | cut -f2- -d'=')
# Visualization folder:
visualization:=$(shell grep  -o 'visualization=[^\]*' config.txt | cut -f2- -d'=')
# Code folder:
code:=$(shell grep  -o 'code=[^\]*' config.txt | cut -f2- -d'=')

#==============================================================================#
# 			PostgreSQL connection parameters		       #
#==============================================================================#

postgres_user_name=$(shell grep  -o 'postgres_user_name=[^\]*' config.txt | cut -f2- -d'=')
postgres_port_number=$(shell grep  -o 'postgres_port_number=[^\]*' config.txt | cut -f2- -d'=')
postgres_hostname=$(shell grep  -o 'postgres_hostname=[^\]*' config.txt | cut -f2- -d'=')
postgres_password=$(shell grep  -o 'postgres_password=[^\]*' config.txt | cut -f2- -d'=')


#===============================================================================#
#		                 MAKEFILE			      	        #
#===============================================================================#

all: osmosis1 osmosis2 osmosis_merge postgis postgres osm2pgsql abstraction 

#===============================================================================#
# Step4: Execute the abstraction on the power database				
#===============================================================================#

abstraction: $(code)/SciGRID.py  
	@echo ${\n} '#=============================================================================='
	@echo ${\n}
	@echo 'Step4 Running the abstraction script SciGRID.py on the database' ${db_name} ':'
	@echo ${\n}
	@echo ${\n} '#=============================================================================='
	@echo ${\n}
	@python SciGRID.py -U $(postgres_user_name) -P $(postgres_port_number) -H $(postgres_hostname) -D ${db_name} -X $(postgres_password) 
	@echo ${\n} 
	@echo ${\n} '#=============================================================================='
	@echo ${\n} 
	@echo 'Abstraction successfully completed for database' ${db_name} '.'
	@echo ${\n}
	@echo ${\n} '#=============================================================================='


#===============================================================================#
# Step3: Export the power data to the database created using osm2pgsql
#===============================================================================#

osm2pgsql: 
	@echo ${\n}
	@echo ${\n} '#=============================================================================='
	@echo ${\n}
	@echo  'Step3. Export the power data to the postgrseql database' ${db_name} 'using osm2pgsql:'
	@echo ${\n}
	@echo ${\n} '#=============================================================================='
	@$(osm2pgsql_folder)/osm2pgsql -r pbf --username='$(postgres_user_name)' -d ${db_name} -k -s -C 6000 -v --host='$(postgres_hostname)' --port='$(postgres_port_number)' --password --style $(osm_raw_power_data)/${stylefile_name} $(osm_raw_power_data)/${OSM_power_all}
	@echo ${\n} '#=============================================================================='
	@echo ${\n}
	@echo 'Power data export to database' ${db_name} 'successfully completed.' 
	@echo ${\n}
	@echo ${\n} '#=============================================================================='

#===============================================================================#
# Step2: Create the database to store the OSM power data
#===============================================================================#

postgres: 
	@echo ${\n}
	@echo ${\n} '#=============================================================================='
	@echo ${\n}
	@echo 'Step2. Create database' ${db_name}
	@echo ${\n}
	@psql --username='$(postgres_user_name)' --dbname='$(postgres_user_name)' -q --host='$(postgres_hostname)' -c "CREATE DATABASE ${db_name} WITH TEMPLATE = ${postgis_name};"
	@echo ${\n}
	@echo ${\n} '#=============================================================================='
	@echo ${\n}
	@echo 'Database' ${db_name} 'successfully created.' 
	@echo ${\n}
	@echo ${\n} '#=============================================================================='
  
#===============================================================================#
# Step1: Create the postgis template with hstore extension.
#===============================================================================#

postgis: 
	@echo ${\n}
	@echo ${\n} '#=============================================================================='
	@echo ${\n}
	@echo 'Step1.1 Create ' ${postgis_name} 'postgis template'
	@echo ${\n}
	@echo ${\n}
	@createdb --username='$(postgres_user_name)' --host='$(postgres_hostname)' ${postgis_name}
	@echo 'Postgis database successfully created.'
	@echo ${\n}
	@echo ${\n} '#=============================================================================='
	@echo ${\n}
	@echo 'Step1.2 Install postgis' 
	@echo ${\n}
	@psql -d ${postgis_name} --username='$(postgres_user_name)' -q --host='$(postgres_hostname)' -f $(postgis_folder)/postgis.sql
	@echo 'Postgis successfully installed.'
	@echo ${\n}
	@echo ${\n} '#=============================================================================='
	@echo ${\n}
	@echo 'Step1.3 Install the spatial reference system for postgis'
	@echo ${\n}
	@psql -d ${postgis_name} --username='$(postgres_user_name)' -q --host='$(postgres_hostname)' -f $(postgis_folder)/spatial_ref_sys.sql
	@@echo 'Spatial reference system for postgis successfully installed.'
	@echo ${\n}
	@echo ${\n} '#=============================================================================='
	@echo ${\n}
	@echo 'Step1.4 Create the hstore extension for the postgis template' ${postgis_name}
	@echo ${\n}
	@echo ${\n}
	@psql -d ${postgis_name} --username='$(postgres_user_name)' -q --host='$(postgres_hostname)' -c "CREATE EXTENSION hstore;"
	@echo ${\n}	
	@echo 'Hstore extension successfully created.'
	@echo ${\n}

#===============================================================================#
# Step0: Extract the raw OSM data as .pbf file from the file planet-latest.osm.pbf
#===============================================================================#

osmosis_merge: osmosis1 osmosis2
	@echo ${\n}
	@echo ${\n} '#=============================================================================='
	@echo ${\n}
	@echo 'Step0.3 Merge the extracted power data from planet OSM raw data using Osmosis:'
	@echo ${\n}
	@echo ${\n} '#=============================================================================='
	@$(osmosis_folder)/osmosis \
	--read-pbf file='$(osm_raw_power_data)/$(OSM_power_extract1)' \
	--read-pbf file='$(osm_raw_power_data)/$(OSM_power_extract2)' \
	--merge --write-pbf file='$(osm_raw_power_data)/$(OSM_power_all)'
	@echo ${\n} '#=============================================================================='
	@echo ${\n}
	@echo 'Power data successfully filtered from planet OSM raw data.'


osmosis2: 
	@echo ${\n}
	@echo ${\n} '#=============================================================================='
	@echo ${\n}
	@echo 'Step0.2 Filter the power "route" data from planet OSM raw data using Osmosis:'
	@echo ${\n}
	@echo ${\n} '#=============================================================================='
	@$(osmosis_folder)/osmosis \
	--read-pbf file='$(osm_raw_data)/$(OSM_raw)' \
	--tag-filter accept-relations route=power \
	--used-way \
	--used-node \
	--buffer \
	--bounding-box top=56.0 bottom=46.0 left=5.0 right=16.0 completeRelations=yes \
	--write-pbf file='$(osm_raw_power_data)/$(OSM_power_extract2)'
	@echo ${\n} '#=============================================================================='
	@echo ${\n}
	@echo 'Power route data successfully filtered from planet OSM raw data.'


osmosis1:
	@echo ${\n}
	@echo ${\n} '#=============================================================================='
	@echo ${\n}
	@echo 'Step0.1 Filter the relation, ways and nodes power data from planet OSM raw data using Osmosis:'
	@echo ${\n}
	@echo ${\n} '#=============================================================================='
	@$(osmosis_folder)/osmosis \
	--read-pbf file='$(osm_raw_data)/$(OSM_raw)' \
	--tag-filter accept-relations power=* \
	--tf accept-ways power=* --tf accept-nodes power=* \
	--used-node --buffer \
	--bounding-box top=56.0 bottom=46.0 left=5.0 right=16.0 completeRelations=yes \
	--write-pbf file='$(osm_raw_power_data)/$(OSM_power_extract1)'
	@echo ${\n} '#=============================================================================='
	@echo ${\n}
	@echo 'Power data for relations, ways and nodes successfully filtered from planet OSM raw data.'
#=========================================================================================================
