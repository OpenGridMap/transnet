from shapely.geometry import Point


class City:
    def __init__(self, population, lat, lon, name):
        self.population = population
        self.lat = lat
        self.lon = lon
        self.geom = Point(lon, lat)
        self.name = name
