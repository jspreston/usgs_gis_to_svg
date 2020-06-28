import json
import itertools
import os

from osgeo import gdal
import drawSvg as draw

def extract_topo_data(gis_data, layer_name):
    # We're only interested in the elevation contours.  We'll read each
    # feature in this layer and convert it to a simple json representation
    elev_layer = gis_data.GetLayerByName(layer_name)
    n_features = elev_layer.GetFeatureCount()
    features = [elev_layer.GetFeature(idx) for idx in range(1,n_features+1)]
    features_json = [json.loads(f.ExportToJson()) for f in features]

    # extract just the 2D geometry of the contour lines
    lines = [f['geometry']['coordinates'][0] for f in features_json]
    return lines


def extents(gis_data_list, layer_name):
    extents = [
        gis_data.GetLayerByName(layer_name).GetExtent()
        for gis_data in gis_data_list
    ]
    xmins, xmaxes, ymins, ymaxes = [list(l) for l in zip(*extents)]
    xmin = min(xmins)
    xmax = max(xmaxes)
    ymin = min(ymins)
    ymax = max(ymaxes)
    return xmin, xmax, ymin, ymax
        

# just hard-code this for now
BASE_DIR = "/home/jsam/winHome/Documents/personal/topo_maps"
GIS_FILES = [
    os.path.join(BASE_DIR, "VECTOR_Seattle_North_WA_7_5_Min_GDB.zip"),
    os.path.join(BASE_DIR, "VECTOR_Seattle_South_WA_7_5_Min_GDB.zip"),
    os.path.join(BASE_DIR, "VECTOR_Shilshole_Bay_WA_7_5_Min_GDB.zip"),
    os.path.join(BASE_DIR, "VECTOR_Duwamish_Head_WA_7_5_Min_GDB.zip")
]
LAYER_NAME = "Elev_Contour"

# gdal python wrappers don't raise exceptions by default
gdal.UseExceptions()

if __name__ == "__main__":

    data = [gdal.ogr.Open(fname) for fname in GIS_FILES]

    # just for initial check, print the lauyer names
    n_layers = data[0].GetLayerCount()
    layers = [data[0].GetLayerByIndex(idx) for idx in range(n_layers)]
    print([l.GetName() for l in layers])

    lines = list(itertools.chain(*[
        extract_topo_data(_data, LAYER_NAME) for _data in data
    ]))
    # this layer comes with extent information that we can use when
    # defining the svg
    xmin, xmax, ymin, ymax = extents(data, LAYER_NAME)

    # Now create the SVG image

    # remember we're working with coordinates in degrees, so the pixel
    # scale is very large and stroke width needs to be very small
    PIXEL_SCALE=10000
    STROKE_WIDTH=1.0/PIXEL_SCALE
    STROKE_COLOR='#00aa00'
    d = draw.Drawing(
        xmax-xmin,
        ymax-ymin,
        origin=(xmin, ymin),
        displayInline=False
    )
    for line in lines:
        linepoints = list(itertools.chain(*[(pt[0], pt[1]) for pt in line]))
        d.append(
            draw.Lines(
                *linepoints,
                close=False,
                stroke_width=STROKE_WIDTH,
                fill='none',
                # fill='#eeee00',
                stroke=STROKE_COLOR))
    d.setPixelScale(PIXEL_SCALE)  # Set number of pixels per geometry unit
    # d.setRenderSize(400,200)  # Alternative to setPixelScale
    d.saveSvg('contours.svg')
