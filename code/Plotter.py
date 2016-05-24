import matplotlib.pyplot as plt
from matplotlib import cm
cmap = cm.spectral


class Plotter:
    def __init__(self):
        None

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
                        linewidth=3, solid_capstyle='round', zorder=2)

        for circuit in circuits:
            plt.plot(circuit.members[0].lon, circuit.members[0].lat, marker='o', markerfacecolor='black', linestyle="None", markersize=3, zorder=2)
            plt.plot(circuit.members[-1].lon, circuit.members[-1].lat, marker='o', markerfacecolor='black',
                     linestyle="None", markersize=3, zorder=2)

            start_of_link = [circuit.members[0].lon, circuit.members[0].lat]
            end_of_link = [circuit.members[-1].lon, circuit.members[-1].lat]
            plt.plot(*zip(start_of_link, end_of_link), color=cmap(int(255 * ((int(circuit.voltage) - 110000) / 340000.0))), lw=1.3,
                     zorder=1)

        plt.plot([], [], marker='o', markerfacecolor='black', linestyle="None", markersize=3, zorder=2,
                 label='substation')
        for voltage in [110000,220000,380000]:
            if voltage >= 380000 and voltage <= 400000:
                plt.plot([], [], color=cmap(int(255 * ((390000 - 110000) / 340000.0))), lw=1.3, zorder=2,
                         label="380-400 kV transmission line")
            else:
                plt.plot([], [], color=cmap(int(255 * ((voltage - 110000) / 340000.0))), lw=1.3, zorder=2,
                         label=str(int(voltage / 1000.0)) + " kV transmission line")
        l = plt.legend(numpoints=1, loc=1)
        l.set_zorder(3)

        plt.savefig('../results/topology.png', bbox_inches='tight', pad_inches=0, dpi=600)