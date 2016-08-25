import matplotlib.pyplot as plt
from matplotlib import cm
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.io.shapereader as shpreader
from matplotlib.offsetbox import AnchoredText
import matplotlib.patches as patches
import matplotlib.image as image

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
                    self.thickness_dict[voltage] = 1
                    self.zorder_dict[voltage] = 1
                elif int(voltage) / 220000 > 0:
                    self.thickness_dict[voltage] = 0.75
                    self.zorder_dict[voltage] = 2
                else:
                    self.thickness_dict[voltage] = 0.5
                    self.zorder_dict[voltage] = 3

    def plot_topology(self, circuits, equpipments_multipoint, partition_by_station_dict, cities, destdir):

        (ymin, xmin, ymax, xmax) = equpipments_multipoint.buffer(0.2).bounds
        sidebar_width = (xmax - xmin) * 0.4
        sidebar_height = ymax - ymin

        ax = plt.axes(projection=ccrs.PlateCarree())
        ax.set_extent([xmin, xmax + sidebar_width, ymin, ymax])
        ax.stock_img()
        ax.coastlines(resolution='10m', color='gray')
        ax.add_feature(cfeature.BORDERS, color='gray')

        #if hasattr(boundary, 'geoms'):
        #    for polygon in boundary.geoms:
        #        Plotter.plot_polygon(polygon)
        #else:
        #    Plotter.plot_polygon(boundary)


        for circuit in circuits:
            plt.plot(circuit.members[0].lon, circuit.members[0].lat, marker='o', markerfacecolor='black',
                     linestyle="None", markersize=1, zorder=10, transform=ccrs.PlateCarree())
            plt.plot(circuit.members[-1].lon, circuit.members[-1].lat, marker='o', markerfacecolor='black',
                     linestyle="None", markersize=1, zorder=10, transform=ccrs.PlateCarree())
            # ax.annotate(circuit.members[0].id, (circuit.members[0].lon, circuit.members[0].lat))
            # ax.annotate(circuit.members[-1].id, (circuit.members[-1].lon, circuit.members[-1].lat))

            for line in circuit.members[1:-1]:
                x, y = line.geom.xy
                plt.plot(x, y, color=self.color_dict[line.voltage.split(';')[0]], alpha=1,
                         linewidth=self.thickness_dict[line.voltage.split(';')[0]], solid_capstyle='round',
                         zorder=self.zorder_dict[line.voltage.split(';')[0]], transform=ccrs.PlateCarree())

        if cities is not None:
            for city in cities:
                if city.geom.within(equpipments_multipoint.buffer(0.2).bounds):
                    plt.plot(city.lon, city.lat, marker='s', markerfacecolor='#ff0000', linestyle="None",
                             markersize=log(city.population, 10), zorder=1.5)
                    if city.population >= 200000 and 'DEUTSCHLAND' not in city.name:
                        label = city.name
                        ax.annotate(label, (city.lon, city.lat))

        # sidebar
        ax.add_patch(patches.Rectangle((xmax, ymin), sidebar_width, sidebar_height, facecolor="white", zorder=10))
        im = image.imread('../util/logo2.png')
        ax.imshow(im, aspect='auto', extent=(xmax+sidebar_width/4, xmax+3*sidebar_width/4, ymax-sidebar_height/3, ymax-sidebar_height/2), zorder=11)
        text = AnchoredText('(c) OpenGridMap', loc=1, prop={'size': 12}, frameon=True, borderpad=0.8)
        text.set_zorder(11)
        ax.add_artist(text)
        plt.plot([], [], marker='s', markerfacecolor='black', linestyle="None", markersize=1, zorder=11, label='station')
        for voltage in self.color_dict.keys():
            label = voltage + 'V'
            plt.plot([], [], color=self.color_dict[voltage], lw=self.thickness_dict[voltage], zorder=11, label=label)
        l = plt.legend(numpoints=1, loc=4)
        l.set_zorder(11)

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