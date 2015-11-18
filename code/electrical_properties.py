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

import psycopg2
from optparse import OptionParser

def add_dena_assumptions(cur,conn):
    """ Define specific electrical properties using the dena (Deutsche Energie-Agentur) study of 2012. 
        The factor /1000 is used to express the electrical properties in /km units"""
    sql =   """
            SELECT l_id,length_m,cables,voltage,wires FROM links;
            """
    cur.execute(sql)
    results = cur.fetchall()
    nr_success = 0
    for res in results:
        length_km = False if res[1] == None else float(res[1]) / 1000.0 
        cables = False if res[2] == None else int(res[2]) 
        voltage = False if res[3] == None else int(res[3]) 
        wires = False if res[4] == None else int(res[4]) 
        
        if (length_km != False and cables != False and voltage != False and wires != False) == True:
           
	      # Specific resistance of the transmission lines.
            coeff_r = 0.08 if voltage == 220000 else 0.025 if voltage == 380000 else None
            r = length_km * coeff_r / (cables / 3.0) / wires
            
            # Specific reactance of the transmission lines.
            coeff_x = 0.32 if voltage == 220000 else 0.25 if voltage == 380000 else None
            x = length_km * coeff_x 
            
	      # Specific capacitance of the transmission lines.
            coeff_c = 11.5 if voltage == 220000 else 13.7 if voltage == 380000 else None
            c = length_km * coeff_c
            
	      # Specific maximum current of the transmission lines.
            coeff_i = 1.3 if voltage == 220000 else 2.6 if voltage == 380000 else None            
            i = length_km * coeff_i * (cables / 3.0) * wires
            
            
            sql =   """
                    UPDATE links SET r='%f', x='%f', c='%f', i_th_max='%f' WHERE l_id='%s';
                    """ % (r, x, c, i, res[0])
            cur.execute(sql)
            conn.commit()
            
            nr_success += 1
        else:
            continue
    
    return nr_success
    

def add_your_assumptions(cur,conn):
    # Implement if other assumptions and sources are considered to calculate the transmission lines electrical properties
    pass

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
        print "Could not connect to database. Please check the values of host,port,user,password,database name."
        parser.print_help()
        exit() 
    
    try:
        nr_success = add_dena_assumptions(cur,conn)
        print 'Calculated electrical properties: %i' %(nr_success)
    except:
        print 'ERROR: Could not add electrical properties to links in database.'
        exit()
    
    
    

	
