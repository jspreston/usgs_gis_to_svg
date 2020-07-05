import json
import itertools
import os
import collections
import math

from osgeo import gdal
import drawSvg as draw
import numpy as np
import matplotlib.pyplot as plt

from plot_utils import ColoredLinePlotter
from contour_utils import ContourCloser

def extract_layer_features(gis_data, layer_name):
    # We're only interested in the elevation contours.  We'll read each
    # feature in this layer and convert it to a simple json representation
    layer = gis_data.GetLayerByName(layer_name)
    n_features = layer.GetFeatureCount()
    features = [layer.GetFeature(idx) for idx in range(1,n_features+1)]
    features_json = [json.loads(f.ExportToJson()) for f in features]
    return features_json


def get_topo_lines(topo_features_json_list):
    topo_lines = collections.defaultdict(list)
    for topo_features_json in topo_features_json_list:
        # collect lines by elevation
        for f in topo_features_json:
            elevation = f["properties"]["ContourElevation"]
            topo_lines[elevation].append(f['geometry']['coordinates'][0])
    return dict(topo_lines)


# just hard-code this for now
BASE_DIR = "/home/jsam/winHome/Documents/personal/topo_maps"
GIS_FILES = [
    os.path.join(BASE_DIR, "VECTOR_Seattle_North_WA_7_5_Min_GDB.zip"),
    os.path.join(BASE_DIR, "VECTOR_Seattle_South_WA_7_5_Min_GDB.zip"),
    os.path.join(BASE_DIR, "VECTOR_Shilshole_Bay_WA_7_5_Min_GDB.zip"),
    os.path.join(BASE_DIR, "VECTOR_Duwamish_Head_WA_7_5_Min_GDB.zip")
]
TOPO_LAYER_NAME = "Elev_Contour"

# gdal python wrappers don't raise exceptions by default
gdal.UseExceptions()

if __name__ == "__main__":

    data = gdal.ogr.Open(GIS_FILES[0])

    # just for initial check, print the lauyer names
    n_layers = data.GetLayerCount()
    layers = [data.GetLayerByIndex(idx) for idx in range(n_layers)]
    print([l.GetName() for l in layers])

    topo_json = extract_layer_features(data, TOPO_LAYER_NAME)
    bbox = data.GetLayerByName(TOPO_LAYER_NAME).GetExtent()
    cc = ContourCloser(bbox)

    lines_by_elevation = get_topo_lines([topo_json])

    def plot_line(l, **kwargs):
        x, y, z = [list(coords) for coords in zip(*l)]
        plt.plot(x, y, **kwargs)
        
    
    elevation = 20
    for line in lines_by_elevation[elevation]:
        closed_line = cc.close_contour(line)
        fig = plt.figure('closed contour')
        fig.clf()
        plot_line(closed_line, color='g')
        plot_line(line, color='r')
        plt.show()
