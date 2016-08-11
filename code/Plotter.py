import matplotlib.pyplot as plt
from matplotlib import cm
cmap = cm.spectral
from math import log
import logging

root = logging.getLogger()

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

    def plot_topology(self, circuits, boundary, partition_by_station_dict, cities, destdir):
        fig = plt.figure(figsize=(10, 12), facecolor='white')
        ax = plt.subplot(111)
        ax.set_axis_off()
        fig.add_axes(ax)

        if boundary is not None:
            (xmin, ymin, xmax, ymax) = boundary.buffer(0.5).bounds
            plt.xlim([xmin, xmax])
            plt.ylim([ymin, ymax])
            if hasattr(boundary, 'geoms'):
                for polygon in boundary.geoms:
                    Plotter.plot_polygon(polygon)
            else:
                Plotter.plot_polygon(boundary)

        for circuit in circuits:
            plt.plot(circuit.members[0].lon, circuit.members[0].lat, marker='o', markerfacecolor='black', linestyle="None", markersize=5, zorder=10)
            plt.plot(circuit.members[-1].lon, circuit.members[-1].lat, marker='o', markerfacecolor='black',
                     linestyle="None", markersize=5, zorder=10)
            #ax.annotate(circuit.members[0].id, (circuit.members[0].lon, circuit.members[0].lat))
            #ax.annotate(circuit.members[-1].id, (circuit.members[-1].lon, circuit.members[-1].lat))

            for line in circuit.members[1:-1]:
                x,y = line.geom.xy
                plt.plot(x, y, color=self.color_dict[line.voltage.split(';')[0]], alpha=1,
                        linewidth=self.thickness_dict[line.voltage.split(';')[0]], solid_capstyle='round', zorder=self.zorder_dict[line.voltage.split(';')[0]])

        if cities is not None:
             for city in cities:
                if city.geom.within(boundary):
                    plt.plot(city.lon, city.lat, marker='o', markerfacecolor='#ff0000', linestyle="None", markersize=log(city.population, 10), zorder=2)
                    if city.population >= 200000 and 'DEUTSCHLAND' not in city.name:
                        label = city.name
                        ax.annotate(label, (city.lon, city.lat))

        plt.plot([], [], marker='o', markerfacecolor='black', linestyle="None", markersize=5, zorder=5, label='station')
        for voltage in self.color_dict.keys():
            label = voltage + 'V'
            plt.plot([], [], color=self.color_dict[voltage], lw=1.3, zorder=5, label=label)
        l = plt.legend(numpoints=1, loc=2)
        l.set_zorder(5)

        plt.savefig(destdir + '/topology.png', bbox_inches='tight', pad_inches=0, dpi=600)

        # Voronoi partitions
        if partition_by_station_dict is not None:
            for station in partition_by_station_dict.keys():
                partition_polygon = partition_by_station_dict[station]
                if hasattr(partition_polygon, 'geoms'):
                    for polygon in partition_polygon:
                        Plotter.plot_polygon(polygon, '#888888', zorder=2)
                else:
                    Plotter.plot_polygon(partition_polygon, '#888888', zorder=2)
            plt.plot([], [], color='#888888', lw=2, zorder=5, label='Voronoi partitions')
            plt.savefig(destdir + '/topology_voronoi.png', bbox_inches='tight', pad_inches=0, dpi=600)


    @staticmethod
    def plot_polygon(polygon, color='#cccccc', zorder=1):
        x, y = polygon.exterior.xy
        plt.plot(x, y, color=color, alpha=1,
                 linewidth=2, solid_capstyle='round', zorder=zorder)