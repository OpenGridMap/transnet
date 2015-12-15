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

from optparse import OptionParser
import psycopg2
import csv


def table_vertices_to_CSV(cur,conn):
    # Stores the vertices table in a csv file
    destination = '../data/03_network/'
    sql = "SELECT current_database();"
    cur.execute(sql)    
    dbname = cur.fetchone()[0]
    filename = destination + 'vertices_' + dbname + '.csv'
    
    try:
        # First, determine the header of the CSV file which contains the column names
        sql =   """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='vertices';
                """   
        cur.execute(sql)
        column_names = cur.fetchall()
        HEADER = [''] * len(column_names)
        for index, column_name in enumerate(column_names):
            HEADER[len(column_names) - index - 1] = column_name[0]
        
        # Second, write a csv file containing the vertices data
        sql = 'SELECT * FROM vertices ORDER BY v_id;'
        cur.execute(sql)
        records = cur.fetchall()
        with open(filename, 'w') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(HEADER)
            for row in records:
                writer.writerow(row)
    except:
        return 0 #"ERROR: Could not write CSV file for table 'vertices'!"
    return 1 #"Done. Writing CSV file for table 'vertices'."

def table_links_to_CSV(cur,conn):
    destination = '../data/03_network/'
    sql = "SELECT current_database();"
    cur.execute(sql)    
    dbname = cur.fetchone()[0]
    filename = destination + 'links_' + dbname + '.csv'
    
    try:
        # First, determine the header of the CSV file which contains the column names
        sql =   """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='links';
                """   
        cur.execute(sql)
        column_names = cur.fetchall()
        HEADER = [''] * len(column_names)
        for index, column_name in enumerate(column_names):
            HEADER[len(column_names) - index - 1] = column_name[0]
        
        # Second, write a csv file with the vertices data
        sql = 'SELECT * FROM links ORDER BY l_id;'
        cur.execute(sql)
        records = cur.fetchall()
        
        with open(filename, 'w') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(HEADER)
            for row in records:
                writer.writerow(row)
    except:
        return 0 #"ERROR: Could not write CSV file for table 'links'!"
    return 1 #"Done. Writing CSV file for table 'links'."


def save_tables_to_CSVs(cur,conn):
    msg1 = table_vertices_to_CSV(cur,conn)
    msg2 = table_links_to_CSV(cur,conn)
    return (msg1 + msg2)


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
        conn = psycopg2.connect(database=dbname, user=dbuser, port=dbport, host=dbhost, password=dbpwrd)
        cur = conn.cursor()
    except:
        print "Could not connect to database. Please check the valus of host,port,user,password,database name."
        parser.print_help()
        exit() 
      
    try:
        msg = save_tables_to_CSVs(cur,conn)
        print 'CSV files for vertices and links written: ', msg
    except:
        print 'ERROR: Could not create cvs files with vertices and links from database.'
        exit()
    

