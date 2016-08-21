from shapely.geometry import Point


class City:
    population = None
    lat = None
    lon = None
    geom = None
    name = None

    def __init__(self, population, lat, lon, name):
        self.population = population
        self.lat = lat
        self.lon = lon
        self.geom = Point(lon, lat)
        self.name = name
