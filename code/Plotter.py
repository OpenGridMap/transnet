import matplotlib.pyplot as plt
from matplotlib import cm
cmap = cm.spectral


class Plotter:
    def __init__(self):
        None

    color_dict = dict()
    color_dict['110000'] = '#ff0000'
    color_dict['220000'] = '#00ff00'
    color_dict['380000'] = '#0000ff'
    thickness_dict = dict()
    thickness_dict['110000'] = 1
    thickness_dict['220000'] = 2
    thickness_dict['380000'] = 3
    zorder_dict = dict()
    zorder_dict['110000'] = 3
    zorder_dict['220000'] = 2
    zorder_dict['380000'] = 1

    @staticmethod
    def plot_topology(circuits, boundary):
        fig = plt.figure(figsize=(10, 12), facecolor='white')
        ax = plt.subplot(111)
        ax.set_axis_off()
        fig.add_axes(ax)

        if boundary is not None:
            for polygon in boundary.geoms:
                x,y = polygon.exterior.xy
                plt.plot(x, y, color='#6699cc', alpha=0.7,
                        linewidth=2, solid_capstyle='round', zorder=1)

        for circuit in circuits:
            plt.plot(circuit.members[0].lon, circuit.members[0].lat, marker='o', markerfacecolor='black', linestyle="None", markersize=5, zorder=4)
            plt.plot(circuit.members[-1].lon, circuit.members[-1].lat, marker='o', markerfacecolor='black',
                     linestyle="None", markersize=5, zorder=4)

            for line in circuit.members[1:-1]:
                x,y = line.geom.xy
                plt.plot(x, y, color=Plotter.color_dict[line.voltage.split(';')[0]], alpha=0.5,
                        linewidth=Plotter.thickness_dict[line.voltage.split(';')[0]], solid_capstyle='round', zorder=Plotter.zorder_dict[line.voltage.split(';')[0]])

            start_of_link = [circuit.members[0].lon, circuit.members[0].lat]
            end_of_link = [circuit.members[-1].lon, circuit.members[-1].lat]
            plt.plot(*zip(start_of_link, end_of_link), color='#333333', alpha=0.2, lw=1.3, zorder=1)

        plt.plot([], [], marker='o', markerfacecolor='black', linestyle="None", markersize=5, zorder=5, label='substation')
        for voltage in Plotter.color_dict.keys():
            label = voltage + 'V transmission line'
            plt.plot([], [], color=Plotter.color_dict[voltage], lw=1.3, zorder=5,
                     label=label)
        l = plt.legend(numpoints=1, loc=1)
        l.set_zorder(3)

        plt.savefig('../results/topology.png', bbox_inches='tight', pad_inches=0, dpi=600)