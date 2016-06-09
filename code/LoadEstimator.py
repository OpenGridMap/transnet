import numpy as np
from scipy.spatial import Voronoi
from scipy.interpolate import Rbf
import mysql.connector
from City import City
import logging
from shapely import wkt
from Plotter import Plotter

root = logging.getLogger()


class LoadEstimator:

    stations = None
    boundary = None
    cities = None
    interpolation_fct = None
    interpolation_map = None

    def __init__(self, stations, boundary):
        self.stations = stations
        self.boundary = boundary
        self.cities = self.find_cities()
        self.interpolation_fct = self.population_interpolation_function()

    def partition(self):
        station_coordinates = []
        for station in self.stations.values():
            station_coordinates.append([station.lon, station.lat])
        points = np.array(station_coordinates)
        return Voronoi(points)

    def find_cities(self):
        (xmin, ymin, xmax, ymax) = self.boundary.bounds
        cnx = mysql.connector.connect(user='root', database='opengeodb')
        cursor = cnx.cursor()

        query = ("select i.int_val, c.lon, c.lat, t.text_val from geodb_intdata i, geodb_coordinates c, geodb_textdata t where"
                 " i.int_type = 600700000 and i.int_val >= 5000 and i.loc_id = c.loc_id and c.loc_id = t.loc_id and t.text_type = 500100002 and lat >= %s and lat <= %s and lon >= %s and lon <= %s")
        cursor.execute(query, (str(ymin), str(ymax), str(xmin), str(xmax)))
        cities = []
        for (population, lon, lat, name) in cursor:
            cities.append(City(population, lat, lon, name))
        cursor.close()
        cnx.close()
        return cities

    def population_interpolation_function(self):
        x = []
        y = []
        p = []
        for city in self.cities:
            x.append(city.lon)
            y.append(city.lat)
            p.append(city.population)
        return Rbf(x, y, p, function='linear', smooth=1)

if __name__=="__main__":
    bpoly = "POLYGON((7.5117 49.7913, 10.4956 49.7913, 10.4956 47.5325, 7.5117 47.5325, 7.5117 49.7913))"
    bayern_bounding_polygon = wkt.loads(bpoly)
    load_estimator = LoadEstimator(dict(), bayern_bounding_polygon)
    cities = load_estimator.cities
    interpolation_fct = load_estimator.interpolation_fct
    root.info('Plot inferred transmission system topology')
    plotter = Plotter('')
    plotter.plot_topology([], bayern_bounding_polygon, None, cities, interpolation_fct)