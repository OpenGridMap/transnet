#!/bin/bash
	
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


# This bash script executes the following tasks:

# Step0. 
#	Filter the raw planet OSM data spatially and thematically.
#	IMPORTANT: Note that this step is **commented out** here. As the OSM planet file has a quite big size, 
#	it is not possible to provide it with the SciGRID model folder. You can download the OSM planet file from: http://planet.openstreetmap.org/planet/

# Step1. 
#	Create the postgis template database with the hstore extension. If the postgis template the user wants to create already exists two choices exists. 
#        1. Delete/drop the existing postgis template and create a new one with the same name. 
#        2. Exit the script and change the name of the postgis template in the config.txt file. The user needs to re run the script after changing the postgis database name. 

# Step2. 
#	 Create an empty database using the postgis and hstore extensions created in step1. 
#        The empty database will hold the power data to be extracted from the filtered OSM data file. 
#        If the database to be created exists, the user has the choice to either:
#        1. Delete/drop the existing database and create a new one with the same name.
#	 2. Rename the database by entering a new name in the screen prompt.

# Step3. 
#	Export the OSM filtered power data filtered in step0 using osm2pgsql to the database created in Step2.

# Step4. 
#	Execute the abstraction script on the database created in Step2 to obtain the abstracted transmission network.

# Step5. 
#	Stores the vertices and links of the abstracted network to a .csv file. 


#========================================================================================================#
# Define the different files paths, files names and database names following in the config.txt file      #	
#========================================================================================================# 

#==============================================================================#
# 			    Databases and files names			       #	
#==============================================================================# 

# Database name (to be set in the config.txt file)
db_name=$(grep -o 'db_name=[^\n]*' config.txt | cut -f2- -d'=');
# Name of the OSM raw data file (to be set in the config.txt file)
OSM_raw=$(grep -o 'OSM_raw=[^\]*' config.txt | cut -f2- -d'=');
OSM_power_extract1=$(grep -o 'OSM_power_extract1=[^\]*' config.txt | cut -f2- -d'=');
OSM_power_extract2=$(grep -o 'OSM_power_extract2=[^\]*' config.txt | cut -f2- -d'=');
OSM_power_all=$(grep -o 'OSM_power_all=[^\]*' config.txt | cut -f2- -d'=');


#==============================================================================#
# 			    Style file and tools location	               #	
#==============================================================================# 

# Name of the stylefile (to be set in the config.txt file)
stylefile_name=$(grep -o 'stylefile_name=[^\]*' config.txt | cut -f2- -d'=');
# Name of the postgis database (to be set in the config.txt file)
postgis_name=$(grep -o 'postgis_name=[^\]*' config.txt | cut -f2- -d'=');
# Location of the Osmosis binary executable.
osmosis_folder=$(grep -o 'osmosis_folder=[^\]*' config.txt | cut -f2- -d'=');
# Location of Osm2pgSQL
osm2pgsql_folder=$(grep -o 'osm2pgsql_folder=[^\]*' config.txt | cut -f2- -d'=');
# postgis.sql and spatial_ref_sys.sql files location:
postgis_folder=$(grep -o 'postgis_folder=[^\]*' config.txt | cut -f2- -d'=');


#==============================================================================#
#                 Environment varibles setting (folder paths)		       #
#==============================================================================#

     # The paths indicated here are relative to the folder SciGRID/code/scripts

# OSM raw data folder:
osm_raw_data=$(grep  -o 'osm_raw_data=[^\]*' config.txt | cut -f2- -d'=')
# OSM raw power data folder:
osm_raw_power_data=$(grep  -o 'osm_raw_power_data=[^\]*' config.txt | cut -f2- -d'=')
# Abstraction folder:
abstraction_folder=$(grep  -o 'abstraction_folder=[^\]*' config.txt | cut -f2- -d'=')
# Network (output) folder:
network=$(grep  -o 'network=[^\]*' config.txt | cut -f2- -d'=')
# Visualization folder:
visualization=$(grep  -o 'visualization=[^\]*' config.txt | cut -f2- -d'=')
# Code folder:
code=$(grep  -o 'code=[^\]*' config.txt | cut -f2- -d'=')


#==============================================================================#
# 			PostgreSQL connection parameters		       #
#==============================================================================#


postgres_user_name=$(grep -o 'postgres_user_name=[^\]*' config.txt | cut -f2- -d'=');
postgres_port_number=$(grep -o 'postgres_port_number=[^\]*' config.txt | cut -f2- -d'=');
postgres_hostname=$(grep -o 'postgres_hostname=[^\]*' config.txt | cut -f2- -d'=');

#===============================================================================#
#		                 Shell Script			      	        #
#===============================================================================#

#===============================================================================#
# Step0: Extract the raw OSM data as .pbf file from the file planet-latest.osm.pbf  
#===============================================================================#


echo -e '#==============================================================================\n';
echo -e 'Step 0.1: Filter the relation, ways and nodes power data from planet OSM raw data using Osmosis.\n'
echo -e '#==============================================================================\n';

$osmosis_folder/osmosis  \
 --read-pbf file=$osm_raw_data/$OSM_raw \
 --tag-filter accept-relations power=*  \
 --tag-filter accept-ways power=*  \
 --tag-filter accept-nodes power=*  \
 --used-node \
 --buffer \
 --bounding-box top=56.0 bottom=46.0 left=5.0 right=16.0 completeRelations=yes \
 --write-pbf file=$osm_raw_power_data/$OSM_power_extract1
echo -e '#==============================================================================\n';
echo -e 'Power data for relations, ways and nodes successfully filtered from planet OSM raw data. \n'

echo -e '#==============================================================================\n';
echo -e 'Step 0.2: Filter the power "route" data from planet OSM raw data using Osmosis.\n'
echo -e '#==============================================================================\n';

$osmosis_folder/osmosis  \
--read-pbf file=$osm_raw_data/$OSM_raw  \
--tag-filter accept-relations route=power  \
--used-way \
--used-node \
--buffer \
--bounding-box top=56.0 bottom=46.0 left=5.0 right=16.0 completeRelations=yes \
--write-pbf file=$osm_raw_power_data/$OSM_power_extract2
echo -e '#==============================================================================\n';
echo -e 'Power route data successfully filtered from planet OSM raw data. \n'


echo -e '#==============================================================================\n';
echo -e 'Step 0.3: Merge the extracted power data from planet OSM raw data using Osmosis.\n'
echo -e '#==============================================================================\n';

$osmosis_folder/osmosis  \
--read-pbf file=$osm_raw_power_data/$OSM_power_extract1  \
--read-pbf file=$osm_raw_power_data/$OSM_power_extract2 \
--merge \
--write-pbf file=$osm_raw_power_data/$OSM_power_all
echo -e '#==============================================================================\n';
echo -e 'Power data successfully filtered from planet OSM raw data. \n'



#===============================================================================#
# 		Step1: Create the postgis template with hstore extension.  
#===============================================================================#

echo -e '#==============================================================================\n';
echo -e 'Step 1.1: Create postgis ' $postgis_name 'template \n'

if createdb --username=$postgres_user_name --host=$postgres_hostname $postgis_name;
then
   echo -e '#==============================================================================\n'; 	
   echo -e 'Template' $postgis_name 'has been successfully created. \n'
   echo -e '#==============================================================================\n'; 
   echo -e 'Step 1.2: Initializing spatial extentions for' $postgis_name '.\n'
   
   psql -d $postgis_name --username=$postgres_user_name --host=$postgres_hostname -q -f $postgis_folder/postgis.sql;
   
   psql -d $postgis_name --username=$postgres_user_name --host=$postgres_hostname -q -f $postgis_folder/spatial_ref_sys.sql;
   
   echo -e 'Initialization of spatial extentions successful. \n'
   echo -e '#==============================================================================\n'; 
   echo -e 'Step 1.3:  Create the hstore extension for the postgis template for' $postgis_name '.\n';
   
   psql -d $postgis_name --username=$postgres_user_name -q --host=$postgres_hostname -c "CREATE EXTENSION hstore;";
   echo -e '\n'
   echo -e ' hstore extension has been successfully created for' $postgis_name '.\n';

else
   
   echo -e '\n' 
   echo -e " SUGGESTION: Do you want to drop the existing template '$postgis_name' and create a new one with the same name? [Y/n]\n"
   read answer1
   if [ "$answer1" == "Y" ] || [ "$answer1" == "y" ];
   then 
	dropdb --username=$postgres_user_name --host=$postgres_hostname $postgis_name;
        echo -e '#==============================================================================\n'; 
        echo -e ' Old template' $postgis_name 'has been successfully dropped.\n'
	createdb --username=$postgres_user_name --host=$postgres_hostname $postgis_name;
	echo -e ' New template' $postgis_name 'has been successfully created.\n'
	
	if psql -d $postgres_user_name --username=$postgres_user_name --host=$postgres_hostname -q -f $postgis_folder/postgis.sql;
   	echo -e '#==============================================================================\n'; 
	then echo -e "Step 1.2: Initializing spatial extentions for' $postgis_name' \n"; fi
	if psql -d $postgis_name --username=$postgres_user_name --host=$postgres_hostname -q -f $postgis_folder/spatial_ref_sys.sql;
	then echo -e "Initialization of spatial extentions successful \n''\n"; fi
	echo -e 'Step 1.3: Create the hstore extension for the postgis template for' $postgis_name '.\n';
        if psql -d $postgis_name --username=$postgres_user_name -q --host=$postgres_hostname -c "CREATE EXTENSION hstore;";
	then echo -e 'hstore extension has been successfully created for' $postgis_name '.\n'; fi
 	echo -e '#==============================================================================\n'; 
   else 
   	echo -e '#==============================================================================\n';
    	echo -e " You need to change the name of your postgis template in the config.txt file. \n";
    	echo -e ' This script will end here without creating the postgis database.\n'
   	echo -e '#==============================================================================\n';      
	exit
        
   fi
fi

#===============================================================================#
#          Step2: Create the database to store the OSM power data
#===============================================================================#

echo -e '#==============================================================================\n';
echo -e 'Step 2: Creating the database '$db_name'.\n'

var1=$(psql -U $postgres_user_name -h $postgres_hostname -lqt  | cut -d \| -f 1 | grep -w $db_name);

Result=$?

if [[ $Result -eq 1 ]] ;  then
  psql -U $postgres_user_name -d $postgres_user_name -q -h $postgres_hostname -c "CREATE DATABASE $db_name WITH TEMPLATE = $postgis_name;" ; 
  echo -e 'Database '$db_name 'successfully created. \n'
  
elif [[ $Result -eq 0 ]] ;  then
  echo 
  echo -e '#==============================================================================\n' 
  echo -e 'Database' $db_name 'already exists. You have two choices:\n' 
  echo -e '1: Rename the database. \n'
  echo -e '2: Delete the existing' $db_name 'database and create a new one with the same name.\n'
  echo -e '#==============================================================================\n'  
  
  echo -e 'Please enter "1" to rename the database'
  echo -e 'or enter "2" to delete the existing' $db_name 'database.\n'
  echo '#==============================================================================' 	
  read choice
  if [[ "$choice" == "2" ]] ; then 
    echo -e '#==============================================================================\n' 
    echo -e 'Are you really sure you want to delete the database' $db_name 
    echo -e 'and create a new one with the same name? [Y/n]\n';
    echo '#==============================================================================' 
    read answer2 
    if [[ "$answer2" == "Y" ]] || [[ "$answer2" == "y" ]]; then
      psql -U $postgres_user_name -h $postgres_hostname -c 'drop database '$db_name'';
      echo -e '#==============================================================================\n' 
      echo -e 'Database' $db_name 'successfully dropped.\n'
      psql -U $postgres_user_name -d $postgres_user_name -q -h $postgres_hostname -c "CREATE DATABASE $db_name WITH TEMPLATE = $postgis_name;"
      echo -e 'Database' $db_name 'successfully created.\n'
            
    else
      echo -e '#==============================================================================\n' 
      echo -e 'Change the database name in the config.txt file and run this script again. '
      echo -e 'This script will end here without creating the database.\n'
      echo -e '#==============================================================================\n'
      exit
    fi
  elif [[ "$choice" == "1" ]] ; then 
  echo -e 'Please enter a new name for the database:\n' 
  echo -e '#==============================================================================\n' 
  read db_name
  echo -e '\n'
  echo -e 'The new name for the power database is now:' $db_name'.\n'	
  if psql -U $postgres_user_name -d $postgres_user_name -q -h $postgres_hostname -c "CREATE DATABASE $db_name WITH TEMPLATE = $postgis_name;" ; then
    echo -e 'Database' $db_name 'successfully created. \n'
  else 
    echo -e 'The name you entered is not valid. This could be because the new name you entered is already used.'
    echo -e 'Change the database name in the config.txt file and run this script again.\n'
    echo -e 'This script will end here without creating the database.\n'
    echo '#==============================================================================\n'
    exit
  fi

  else
    echo -e '#==============================================================================\n' 
    echo -e 'The option you entered is not valid.\n'
    echo -e 'Change the database name in the config.txt file and run this script again.\n'
    echo -e 'This script will end here without creating the database.\n'
    echo '#=============================================================================='
    exit
  fi
fi


#===============================================================================#
#     Step3: Export the power data to the database created using osm2pgsql
#===============================================================================#


echo -e '#==============================================================================\n';
echo -e 'Step 3: Load the OSM raw data to the postgresql database.\n'
echo -e '#==============================================================================\n';
echo -e 'Please enter your postgres user password: \n'

$osm2pgsql_folder/osm2pgsql -r pbf -U $postgres_user_name -d $db_name -k -s -C 6000 -v -H $postgres_hostname -P $postgres_port_number  --hstore --style $osm_raw_power_data/$stylefile_name $osm_raw_power_data/$OSM_power_all
echo -e '\n';
echo -e ' Data successfully imported to the database' $db_name ' .\n';
echo -e '#==============================================================================\n';
 

#===============================================================================#
#    Step4: Execute the abstraction on the power database	
#===============================================================================#

echo -e 'Step 4: Running the abstraction script on the database' $db_name '.\n'
python $code/SciGRID.py -D $db_name -H $postgres_hostname -U $postgres_user_name -P $postgres_port_number
echo -e '\n';
echo -e 'Abstraction was successfully completed on the database' $db_name ' .'
echo -e '\n';
echo -e '#==============================================================================\n';

