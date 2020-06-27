import json
import itertools

from osgeo import gdal
import drawSvg as draw

# just hard-code this for now
GIS_FILE = "/home/jsam/winHome/Documents/personal/topo_maps/VECTOR_Seattle_North_WA_7_5_Min_GDB.zip"

# gdal python wrappers don't raise exceptions by default
gdal.UseExceptions()

data = gdal.ogr.Open(GIS_FILE)

# just for initial check, print the lauyer names
n_layers = data.GetLayerCount()
layers = [data.GetLayerByIndex(idx) for idx in range(n_layers)]
print([l.GetName() for l in layers])

# We're only interested in the elevation contours.  We'll read each
# feature in this layer and convert it to a simple json representation
elev_layer = data.GetLayerByName("Elev_Contour")
n_features = elev_layer.GetFeatureCount()
features = [elev_layer.GetFeature(idx) for idx in range(1,n_features+1)]
features_json = [json.loads(f.ExportToJson()) for f in features]

# extract just the 2D geometry of the contour lines
lines = [f['geometry']['coordinates'][0] for f in features_json]

# this layer comes with extent information that we can use when
# defining the svg
xmin, xmax, ymin, ymax = elev_layer.GetExtent()

# Now create the SVG image

# remember we're working with coordinates in degrees, so the pixel
# scale is very large and stroke width needs to be very small
PIXEL_SCALE=10000
STROKE_WIDTH=1.0/PIXEL_SCALE
STROKE_COLOR='#00aa00'
d = draw.Drawing(xmax-xmin, ymax-ymin, origin=(xmin, ymin), displayInline=False)
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
