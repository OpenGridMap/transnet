import matplotlib.pyplot as plt
from matplotlib import cm
import numpy as np
cmap = cm.spectral
from math import log

class Plotter:
    color_dict = dict()
    thickness_dict = dict()
    zorder_dict = dict()

    def __init__(self, voltage_levels):
        if voltage_levels:
            for voltage in voltage_levels.split('|'):
                self.color_dict[voltage] = cmap(int(255 * ((int(voltage) - 110000) / 340000.0)))
                if int(voltage) / 300000 > 0:
                    self.thickness_dict[voltage] = 3
                    self.zorder_dict[voltage] = 1
                elif int(voltage) / 220000 > 0:
                    self.thickness_dict[voltage] = 2
                    self.zorder_dict[voltage] = 2
                else:
                    self.thickness_dict[voltage] = 1
                    self.zorder_dict[voltage] = 3

    def plot_topology(self, circuits, boundary, voronoi_partitions, cities, interpolation_fct):
        fig = plt.figure(figsize=(10, 12), facecolor='white')
        ax = plt.subplot(111)
        ax.set_axis_off()
        fig.add_axes(ax)
        (xmin, ymin, xmax, ymax) = boundary.bounds
        plt.xlim([xmin, xmax])
        plt.ylim([ymin, ymax])

        if boundary is not None:
            if hasattr(boundary, 'geoms'):
                for polygon in boundary.geoms:
                    Plotter.plot_polygon(polygon)
            else:
                Plotter.plot_polygon(boundary)

        for circuit in circuits:
            plt.plot(circuit.members[0].lon, circuit.members[0].lat, marker='o', markerfacecolor='black', linestyle="None", markersize=2, zorder=10)
            plt.plot(circuit.members[-1].lon, circuit.members[-1].lat, marker='o', markerfacecolor='black',
                     linestyle="None", markersize=2, zorder=10)

            for line in circuit.members[1:-1]:
                x,y = line.geom.xy
                plt.plot(x, y, color=self.color_dict[line.voltage.split(';')[0]], alpha=1,
                        linewidth=self.thickness_dict[line.voltage.split(';')[0]], solid_capstyle='round', zorder=self.zorder_dict[line.voltage.split(';')[0]])

        if voronoi_partitions is not None:
            for ridge in voronoi_partitions.ridge_vertices:
                if ridge[0] == -1 or ridge[1] == -1:
                    continue
                start_of_ridge = voronoi_partitions.vertices[ridge[0]]
                end_of_ridge = voronoi_partitions.vertices[ridge[1]]
                plt.plot(start_of_ridge[0], start_of_ridge[1], marker='o', markerfacecolor='#888888', linestyle="None", markersize=1, zorder=1)
                plt.plot(end_of_ridge[0], end_of_ridge[1], marker='o', markerfacecolor='#888888', linestyle="None",
                         markersize=1, zorder=1)
                plt.plot(*zip(start_of_ridge, end_of_ridge), color='#888888', alpha=1, lw=0.5, zorder=1)
            plt.plot([], [], color='#888888', lw=0.5, zorder=5, label='Voronoi partitions')

        if cities is not None:
            for city in cities:
                plt.plot(city.lon, city.lat, marker='o', markerfacecolor='#ff0000', linestyle="None",
                         markersize=log(city.population, 10), zorder=2)
                if city.population >= 100000:
                    label = city.name
                    ax.annotate(label, (city.lon, city.lat))

        if interpolation_fct is not None:
            tx = np.linspace(xmin, xmax, 500)
            ty = np.linspace(ymin, ymax, 500)
            xi, yi = np.meshgrid(tx, ty)
            pi = interpolation_fct(xi, yi)
            plt.pcolor(xi, yi, pi)
            plt.colorbar()

        plt.plot([], [], marker='o', markerfacecolor='black', linestyle="None", markersize=1, zorder=5, label='station')
        for voltage in self.color_dict.keys():
            label = voltage + 'V'
            plt.plot([], [], color=self.color_dict[voltage], lw=1.3, zorder=5, label=label)
        l = plt.legend(numpoints=1, loc=2)
        l.set_zorder(5)

        plt.savefig('../results/topology.png', bbox_inches='tight', pad_inches=0, dpi=600)

    @staticmethod
    def plot_polygon(polygon):
        x, y = polygon.exterior.xy
        plt.plot(x, y, color='#cccccc', alpha=1,
                 linewidth=2, solid_capstyle='round', zorder=1)