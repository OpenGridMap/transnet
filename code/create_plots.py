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
import matplotlib.pyplot as plt


def plot_landmass_germany(fig):
    """ Plot landmass of Germany from a gpx file. """
    try:
        import gpxpy
    except:
        print 'Cannot create landmass of Germany, to do so you need the python package gpxpy.'
        return fig
    # Location of the landmass gpx file.
    gpx_file = open('../data/04_visualization/landmass_germany.gpx', 'r')
    gpx = gpxpy.parse(gpx_file)
    
    for track in gpx.tracks:
        for segment in track.segments:
            lat = []
            lon = []
            for point in segment.points:
                lat.append(point.latitude)
                lon.append(point.longitude)
            plt.plot(lon, lat, color = 'black', lw = 0.3, zorder = 1)
    return fig

 
def plot_topology(cur,conn,fig):
    """ Plot the topological transmission network from the vertices and links database."""
    # Query to obtain the network vertices.
    sql = 'SELECT lon, lat FROM vertices ORDER BY v_id;'
    cur.execute(sql)
    vertices = cur.fetchall()
    
    plt.plot(*zip(*vertices), marker='o', markerfacecolor='purple', linestyle="None", markersize=3, zorder=2)
    
    # Query to obtain the network links.
    sql = 'SELECT v_id_1, v_id_2, voltage FROM links ORDER BY voltage'
    cur.execute(sql)
    links = cur.fetchall()
    
    for l in links:
        v_id_1 = vertices[l[0]-1]
        v_id_2 = vertices[l[1]-1]
        if int(l[2]) == 220000:
            color = 'blue'
        elif int(l[2]) == 300000:
            color = 'green'
        elif int(l[2]) == 380000:
            color = 'red'
        elif int(l[2]) == 450000:
            color = 'orange'
        else:
            color = 'black'
        plt.plot(*zip(v_id_1,v_id_2), color = color, lw = 1.3, zorder = 1)
    
    # Creating the legend
    plt.plot([], [], marker='o', markerfacecolor='purple', linestyle="None", markersize=3, zorder=2, label = 'substation')       
    plt.plot([], [], color = 'blue',   lw = 1.3, zorder = 2, label = '220kV line')    
    plt.plot([], [], color = 'green',  lw = 1.3, zorder = 2, label = '300kV line')
    plt.plot([], [], color = 'red',    lw = 1.3, zorder = 2, label = '380kV line')
    plt.plot([], [], color = 'orange', lw = 1.3, zorder = 2, label = '450kV line')
    l = plt.legend(numpoints=1,loc=1)
    l.set_zorder(3)
    return fig


def create_de_topology_plot(cur,conn):
    fig = plt.figure(figsize=(10,12),facecolor = 'white')
    ax = plt.subplot(111)
    ax.set_axis_off()
    fig.add_axes(ax)    
    
    fig = plot_landmass_germany(fig)
    fig = plot_topology(cur,conn,fig)
    
    destination = '../data/04_visualization/'  
    sql = "SELECT current_database();"
    cur.execute(sql)    
    dbname = cur.fetchone()[0]
    filename = destination + 'topology_' + dbname + '.pdf'
    plt.savefig(filename, bbox_inches='tight', pad_inches=0, dpi=600)
    return filename


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
        plots = create_de_topology_plot(cur,conn)
        print 'Plotted: %s'% (str(plots))
    except:
        print 'ERROR: Could not create plot of the network topology.'
        exit()    
    
