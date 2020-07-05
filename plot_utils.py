import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.colors import ListedColormap, BoundaryNorm

class ColoredLinePlotter:

    def __init__(self):
        self._line_segments = None
        self._values = None

    def add_line(self, x, y, values):
        points = np.array([x, y]).T.reshape(-1, 1, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)
        # append an extra value onto values since we've converted from
        # points to point pairs
        values = list(values)
        values = values[:-1]

        if self._line_segments is None:
            self._line_segments = segments
            self._values = values
        else:
            self._line_segments = np.concatenate((self._line_segments, segments), axis=0)
            self._values = np.concatenate((self._values, values), axis=0)
            

    def plot(self, cmap='viridis', ax=None, **kwargs):
        if ax is None:
            ax = plt.gca()
        # norm = plt.Normalize(self._values.min(), self._values.max())
        norm = plt.Normalize(0.0, 1.0)
        lc = LineCollection(self._line_segments, cmap=cmap, norm=norm)
        # Set the values used for colormapping
        lc.set_array(self._values)
        lc.set_linewidth(2)
        line = ax.add_collection(lc)

        ax.autoscale()
        return line
