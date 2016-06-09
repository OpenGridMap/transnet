class City:

    population = None
    lat = None
    lon = None
    name = None

    def __init__(self, population, lat, lon, name):
        self.population = population
        self.lat = lat
        self.lon = lon
        self.name = name