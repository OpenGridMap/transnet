import numpy as np
from scipy.spatial import Voronoi, voronoi_plot_2d
import matplotlib.pyplot as plt


class LoadEstimator:

    load_by_station_dict = ()

    def __init__(self):
        None

    def partition(self, stations):
        station_coordinates = []
        for station in stations.values():
            station_coordinates.append([station.lon, station.lat])

        points = np.array(station_coordinates)
        return Voronoi(points)
        #voronoi_plot_2d(vor)
        #plt.show()


if __name__=="__main__":
    points = np.array([[0, 0], [0, 1], [0, 2], [1, 0], [1, 1], [1, 2], [2, 0], [2, 1], [2, 2]])
    vor = Voronoi(points)
    voronoi_plot_2d(vor)
    plt.show()