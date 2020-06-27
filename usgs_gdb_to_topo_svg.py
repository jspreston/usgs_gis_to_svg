import json
import itertools

from osgeo import gdal
import drawSvg as draw

GIS_FILE = "/home/jsam/winHome/Documents/personal/topo_maps/VECTOR_Seattle_North_WA_7_5_Min_GDB.zip"

gdal.UseExceptions()

data = gdal.ogr.Open(GIS_FILE)

n_layers = data.GetLayerCount()
layers = [data.GetLayerByIndex(idx) for idx in range(n_layers)]
print([l.GetName() for l in layers])

elev_layer = data.GetLayerByName("Elev_Contour")

n_features = elev_layer.GetFeatureCount()
features = [elev_layer.GetFeature(idx) for idx in range(1,n_features+1)]

features_json = [json.loads(f.ExportToJson()) for f in features]

lines = [f['geometry']['coordinates'][0] for f in features_json]

xmin, xmax, ymin, ymax = elev_layer.GetExtent()

#
# 
#
d = draw.Drawing(xmax-xmin, ymax-ymin, origin=(xmin, ymin), displayInline=False)
for line in lines:
    linepoints = list(itertools.chain(*[(pt[0], pt[1]) for pt in line]))
    d.append(
        draw.Lines(
            *linepoints,
            close=False,
            stroke_width=0.0001,
            fill='none',
            # fill='#eeee00',
            stroke='#00aa00'))
d.setPixelScale(10000)  # Set number of pixels per geometry unit
# d.setRenderSize(400,200)  # Alternative to setPixelScale
d.saveSvg('contours.svg')
