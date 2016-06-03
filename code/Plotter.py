import matplotlib.pyplot as plt
from matplotlib import cm
cmap = cm.spectral


class Plotter:
    color_dict = dict()
    thickness_dict = dict()
    zorder_dict = dict()

    def __init__(self, voltage_levels):
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

    def plot_topology(self, circuits, boundary):
        fig = plt.figure(figsize=(10, 12), facecolor='white')
        ax = plt.subplot(111)
        ax.set_axis_off()
        fig.add_axes(ax)

        if boundary is not None:
            if hasattr(boundary, 'geoms'):
                for polygon in boundary.geoms:
                    Plotter.plot_polygon(polygon)
            else:
                Plotter.plot_polygon(boundary)

        for circuit in circuits:
            plt.plot(circuit.members[0].lon, circuit.members[0].lat, marker='o', markerfacecolor='black', linestyle="None", markersize=2, zorder=4)
            plt.plot(circuit.members[-1].lon, circuit.members[-1].lat, marker='o', markerfacecolor='black',
                     linestyle="None", markersize=2, zorder=4)

            for line in circuit.members[1:-1]:
                x,y = line.geom.xy
                plt.plot(x, y, color=self.color_dict[line.voltage.split(';')[0]], alpha=1,
                        linewidth=self.thickness_dict[line.voltage.split(';')[0]], solid_capstyle='round', zorder=self.zorder_dict[line.voltage.split(';')[0]])

            #start_of_link = [circuit.members[0].lon, circuit.members[0].lat]
            #end_of_link = [circuit.members[-1].lon, circuit.members[-1].lat]
            #plt.plot(*zip(start_of_link, end_of_link), color='#333333', alpha=0.2, lw=0.5, zorder=1)

        plt.plot([], [], marker='o', markerfacecolor='black', linestyle="None", markersize=1, zorder=5, label='station')
        for voltage in self.color_dict.keys():
            label = voltage + 'V'
            plt.plot([], [], color=self.color_dict[voltage], lw=1.3, zorder=5,
                     label=label)
        l = plt.legend(numpoints=1, loc=2)
        l.set_zorder(3)

        plt.savefig('../results/topology.png', bbox_inches='tight', pad_inches=0, dpi=600)

    @staticmethod
    def plot_polygon(polygon):
        x, y = polygon.exterior.xy
        plt.plot(x, y, color='#6699cc', alpha=1,
                 linewidth=2, solid_capstyle='round', zorder=1)