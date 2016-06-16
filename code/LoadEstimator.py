import numpy as np
from scipy.spatial import Voronoi
import mysql.connector
from City import City
import logging
from shapely import wkt
from shapely.geometry import Polygon
from Plotter import Plotter

root = logging.getLogger()


class LoadEstimator:

    stations = None
    boundary = None
    cities = None
    interpolation_fct = None

    def __init__(self, stations, boundary):
        self.stations = stations
        self.boundary = boundary
        self.cities = self.find_cities()
        self.interpolation_fct = self.population_interpolation_function()

    def partition(self):
        partition_by_station_dict = dict()
        population_by_station_dict = dict()
        station_coordinates = []
        for station in self.stations.values():
            station_coordinates.append([station.lon, station.lat])
        points = np.array(station_coordinates)
        partitions = Voronoi(points)
        regions, vertices = LoadEstimator.voronoi_finite_polygons_2d(partitions)

        polygons = []
        for region in regions:
            vertices_coordinates = []
            for vertice_index in region:
                vertices_coordinates.append((vertices[vertice_index][0], vertices[vertice_index][1]))
            vertices_coordinates.append(vertices_coordinates[0])
            partition_polygon = Polygon(vertices_coordinates)
            polygons.append(partition_polygon)
            for station in self.stations.values():
                if station.geom.within(partition_polygon):
                    partition_by_station_dict[station.id] = partition_polygon.intersection(self.boundary)
                    population_by_station_dict[station.id] = self.population_of_region(partition_polygon)
                    break
        return partition_by_station_dict, population_by_station_dict


    @staticmethod
    def voronoi_finite_polygons_2d(vor, radius=None):
        """
        Reconstruct infinite voronoi regions in a 2D diagram to finite
        regions.

        Parameters
        ----------
        vor : Voronoi
            Input diagram
        radius : float, optional
            Distance to 'points at infinity'.

        Returns
        -------
        regions : list of tuples
            Indices of vertices in each revised Voronoi regions.
        vertices : list of tuples
            Coordinates for revised Voronoi vertices. Same as coordinates
            of input vertices, with 'points at infinity' appended to the
            end.

        """

        if vor.points.shape[1] != 2:
            raise ValueError("Requires 2D input")

        new_regions = []
        new_vertices = vor.vertices.tolist()

        center = vor.points.mean(axis=0)
        if radius is None:
            radius = vor.points.ptp().max()

        # Construct a map containing all ridges for a given point
        all_ridges = {}
        for (p1, p2), (v1, v2) in zip(vor.ridge_points, vor.ridge_vertices):
            all_ridges.setdefault(p1, []).append((p2, v1, v2))
            all_ridges.setdefault(p2, []).append((p1, v1, v2))

        # Reconstruct infinite regions
        for p1, region in enumerate(vor.point_region):
            vertices = vor.regions[region]

            if all(v >= 0 for v in vertices):
                # finite region
                new_regions.append(vertices)
                continue

            # reconstruct a non-finite region
            ridges = all_ridges[p1]
            new_region = [v for v in vertices if v >= 0]

            for p2, v1, v2 in ridges:
                if v2 < 0:
                    v1, v2 = v2, v1
                if v1 >= 0:
                    # finite ridge: already in the region
                    continue

                # Compute the missing endpoint of an infinite ridge

                t = vor.points[p2] - vor.points[p1]  # tangent
                t /= np.linalg.norm(t)
                n = np.array([-t[1], t[0]])  # normal

                midpoint = vor.points[[p1, p2]].mean(axis=0)
                direction = np.sign(np.dot(midpoint - center, n)) * n
                far_point = vor.vertices[v2] + direction * radius

                new_region.append(len(new_vertices))
                new_vertices.append(far_point.tolist())

            # sort region counterclockwise
            vs = np.asarray([new_vertices[v] for v in new_region])
            c = vs.mean(axis=0)
            angles = np.arctan2(vs[:, 1] - c[1], vs[:, 0] - c[0])
            new_region = np.array(new_region)[np.argsort(angles)]

            # finish
            new_regions.append(new_region.tolist())

        return new_regions, np.asarray(new_vertices)

    def find_cities(self):
        (xmin, ymin, xmax, ymax) = self.boundary.bounds
        cnx = mysql.connector.connect(user='root', database='opengeodb')
        cursor = cnx.cursor()
        query = ("select i.int_val, c.lon, c.lat, t.text_val from geodb_intdata i, geodb_coordinates c, geodb_textdata t where"
                 " i.int_type = 600700000 and i.loc_id = c.loc_id and c.loc_id = t.loc_id and t.text_type = 500100002 and lat >= %s and lat <= %s and lon >= %s and lon <= %s")
        cursor.execute(query, (str(ymin), str(ymax), str(xmin), str(xmax)))
        cities = []
        for (population, lon, lat, name) in cursor:
            cities.append(City(population, lat, lon, name))
        cursor.close()
        cnx.close()
        return cities

    def population_of_region(self, region_polygon):
        population = 0
        for city in self.cities:
            if city.geom.within(region_polygon):
                population += city.population
        return population

    @staticmethod
    def estimate_load(population):
        # German per head power consumption in kWh according to statista (for the year 2015)
        per_head_power_consumption = 7.381
        load_per_head = (per_head_power_consumption * 1000) / (365 * 24)
        total_load = population * load_per_head
        print(str(population) + ' * ' + str(load_per_head) + ' = ' + str(total_load))
        return total_load

if __name__=="__main__":
    bpoly = "POLYGON((7.5117 49.7913, 10.4956 49.7913, 10.4956 47.5325, 7.5117 47.5325, 7.5117 49.7913))"
    #bpoly = "POLYGON((5.87 55.1, 15.04 55.1, 15.04 47.27, 5.87 47.27, 5.87 55.1))"
    bayern_bounding_polygon = wkt.loads(bpoly)
    load_estimator = LoadEstimator(dict(), bayern_bounding_polygon)
    cities = load_estimator.cities
    interpolation_fct = load_estimator.interpolation_fct
    root.info('Plot inferred transmission system topology')
    plotter = Plotter('')
    plotter.plot_topology([], bayern_bounding_polygon, None, cities, interpolation_fct)