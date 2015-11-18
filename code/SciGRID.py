"""							         
Copyright "2015" "NEXT ENERGY"						  
										  
Licensed under the Apache License, Version 2.0 (the "License");		  
you may not use this file except in compliance with the License.	  
You may obtain a copy of the License at					  
										  
http://www.apache.org/licenses/LICENSE-2.0				  

Unless required by applicable law or agreed to in writing, software	  
distributed under the License is distributed on an "AS IS" BASIS,	  
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  
See the License for the specific language governing permissions and	  
limitations under the License.
"""
# Command line usage:
# python SciGRID.py -U db_user -P db_port -D db_name -H db_host
#
# Python object usage:
# SciGRID_instance = SciGRID(database='db_name', user='db_user', \
# port=db_port, password='your_password', host='db_host')

import psycopg2
from optparse import OptionParser
from db_create_tables import create_tables
from relation_analysis import analyze_rels
import relation_abstraction as ra
import electrical_properties as ep
from store_network_as_csv import save_tables_to_CSVs
from create_plots import create_de_topology_plot


class SciGRID:
    """ 
    SciGRID class provides methods for the abstraction of 
    OpenStreetMap power data. 
    """

    def __init__(self, database, user, host, port, password):
        # Initializes the SciGRID class with the database connection parameters.
        # These parameters are: database name, database user, database password, database host and port. 
        # Notice: The password will not be stored.

        self.connection = {'database':database, 'user':user, 'host':host, 'port':port}
        self.connect_to_DB(password)

    def get_connection_data(self):
	# Obtain the database connection parameters. 
        return self.connection
    
    def connect_to_DB(self, password):   
	# Establish the database connection. 
        self.conn = psycopg2.connect(password=password, **self.connection)
        self.cur = self.conn.cursor()

    def reconnect_to_DB(self):
	# Reconnect to the database if connection got lost. 
        msg = "Please enter the database password for \n\t database=%s, user=%s, host=%s, port=%port \nto reconnect to the database: " \
            %(str(self.connection['database']), str(self.connection['user']), str(self.connection['host']), str(self.connection['port'])) 
        password = raw_input(msg)
        self.connect_to_DB(self, password)

    def create_tables(self):
	# Create tables necessary for the abstraction process. 
        create_tables(self.cur, self.conn)
    
    def analyze_relations(self):
	# Analyze the power relations. 
        msg = analyze_rels(self.cur, self.conn)
        return msg
    
    def abstract_relations(self):
	# Execute the abstraction. 
        msg = ra.abstract_2subs(self.cur, self.conn)
        success = ra.abstract_3subs_T_node(self.cur, self.conn)
        #TODO: ra.abstract_3subs_in_row(self.cur, self.conn)
        return len(msg) + success
        
    def add_electrical_properties(self):
	# Calculate the electrical properties of the transmission lines using the dena assumptions. 
        nr_success = ep.add_dena_assumptions(self.cur, self.conn)
        return nr_success

    def create_csv_files(self):
	# Create the csv files containing the vertices and links of the abstracted transmission network. 
        msg = save_tables_to_CSVs(self.cur,self.conn)
        return msg
    
    def create_topology_plot(self):
        # Create a plot of the resulting abstracted (topological) transmission network. 
        # For the moment it is just a plot for the German network.
        plot = create_de_topology_plot(self.cur,self.conn)
        return (plot)
    
if __name__ == '__main__':
    
    parser=OptionParser()
    parser.add_option("-D","--dbname", action="store", dest="dbname", \
    help="database name of the topology network")
    parser.add_option("-H","--dbhost", action="store", dest="dbhost", \
    help="database host address of the topology network")
    parser.add_option("-P","--dbport", action="store", dest="dbport", \
    help="database port of the topology network")
    parser.add_option("-U","--dbuser", action="store", dest="dbuser", \
    help="database user name of the topology network")
    parser.add_option("-X","--dbpwrd", action="store", dest="dbpwrd", \
    help="database user password of the topology network")
    
    (options, args) = parser.parse_args()
    # get connection data via command line or set to default values
    dbname = options.dbname if options.dbname else 'de_power_150601'
    dbhost = options.dbhost if options.dbhost else '127.0.0.1'
    dbport = options.dbport if options.dbport else '5432'
    dbuser = options.dbuser if options.dbuser else 'postgres' 
    dbpwrd = options.dbpwrd if options.dbpwrd else '' 
    
 
    # Connect to DB 
    try:
        SciGRID_instance = SciGRID(database=dbname, user=dbuser, port=dbport, host=dbhost, password=dbpwrd)
    except:
        print "Could not connect to database. Please check the values of host,port,user,password, and database name."
        parser.print_help()
        exit() 
    
    # Excute SciGRID methods
    try:
        SciGRID_instance.create_tables()
        print 'Tables created.'
    except:
        print 'ERROR: Could not create tables in database.'
        exit()
    try:
        msg = SciGRID_instance.analyze_relations()
        print 'Number of analyzed relations: ', len(msg)
    except:
        print 'ERROR: Could not analyze relations in database.'
        exit()
    try:
        nr_success = SciGRID_instance.abstract_relations()
        print 'Number of abstracted relations: ', nr_success
    except:
        print 'ERROR: Could not abstract relations in database.'
        exit()
    try:
        nr_success = SciGRID_instance.add_electrical_properties() 
        print 'Calculated electrical properties: %i' %(nr_success)
    except:
        print 'ERROR: Could not add electrical properties to links in database.'
        exit()
    try:
        msg = SciGRID_instance.create_csv_files()
        print 'CSV files for vertices and links written: ', msg
    except:
        print 'ERROR: Could not create cvs files with vertices and links from database.'
        exit()
    try:
        plots = SciGRID_instance.create_topology_plot()
        # FIXME: return message for plots
        print 'Plotted: %s'% (str(plots))
    except:
        print 'ERROR: Could not create plot of the network topology.'
        exit()
    print "All done. Finished the execution of SciGRID methods"
    

    
    
