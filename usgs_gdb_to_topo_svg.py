import json
import itertools
import os
import collections
import math

from osgeo import gdal
import drawSvg as draw

from contour_utils import ContourCloser, ContourCombiner
from contour_utils import Contour, Pt

SEGMENTS_TO_FLIP = {
    "031508f3-89ca-43ee-8f98-aa1a43f849cc_206",
    "8b03d49b-0e59-4f7a-91f5-7efd4d25046b_216",
}


def extract_layer_features(gis_data, layer_name):
    # We're only interested in the elevation contours.  We'll read each
    # feature in this layer and convert it to a simple json representation
    layer = gis_data.GetLayerByName(layer_name)
    n_features = layer.GetFeatureCount()
    features = [layer.GetFeature(idx) for idx in range(1, n_features+1)]
    features_json = [json.loads(f.ExportToJson()) for f in features]
    return features_json


def get_topo_contours(topo_features_json):
    topo_lines = collections.defaultdict(list)
    # collect lines by elevation
    for f in topo_features_json:
        props = f["properties"]
        elevation = props["ContourElevation"]
        id = props["Permanent_Identifier"] + "_" + str(f["id"])
        line = f['geometry']['coordinates'][0]
        points = [Pt(lat=pt[1], lon=pt[0]) for pt in line]
        contour = Contour(id=id, elevation=elevation, points=points)
        if contour.id in SEGMENTS_TO_FLIP:
            print(f"flipping segment {contour.id}")
            contour.reverse()
        topo_lines[elevation].append(contour)
    return dict(topo_lines)


def extents(gis_data_list, layer_name):
    extents = [
        gis_data.GetLayerByName(layer_name).GetExtent()
        for gis_data in gis_data_list
    ]
    lon_mins, lon_maxes, lat_mins, lat_maxes = [list(l) for l in zip(*extents)]
    lon_min = min(lon_mins)
    lon_max = max(lon_maxes)
    lat_min = min(lat_mins)
    lat_max = max(lat_maxes)
    return lat_min, lat_max, lon_min, lon_max


def interpolate_color(cmin, cmax, cval):
    cval = [
        channel_min*(1.0-cval) + channel_max*cval
        for channel_min, channel_max in zip(cmin, cmax)
    ]
    return f"rgb({int(cval[0])}, {int(cval[1])}, {int(cval[2])})"


# just hard-code this for now
BASE_DIR = "/home/jsam/winHome/Documents/personal/topo_maps"
GIS_FILES = [
    os.path.join(BASE_DIR, "VECTOR_Seattle_North_WA_7_5_Min_GDB.zip"),
    os.path.join(BASE_DIR, "VECTOR_Seattle_South_WA_7_5_Min_GDB.zip"),
    os.path.join(BASE_DIR, "VECTOR_Shilshole_Bay_WA_7_5_Min_GDB.zip"),
    os.path.join(BASE_DIR, "VECTOR_Duwamish_Head_WA_7_5_Min_GDB.zip")
]
TOPO_LAYER_NAME = "Elev_Contour"
WATER_LAYER_NAME = "NHDWaterbody"

# gdal python wrappers don't raise exceptions by default
gdal.UseExceptions()


if __name__ == "__main__":

    data = [gdal.ogr.Open(fname) for fname in GIS_FILES]

    # just for initial check, print the layer names
    n_layers = data[0].GetLayerCount()
    layers = [data[0].GetLayerByIndex(idx) for idx in range(n_layers)]
    print([l.GetName() for l in layers])

    topo_jsons = [
        extract_layer_features(_data, TOPO_LAYER_NAME)
        for _data in data
    ]

    lines_by_elevation_list = [
        get_topo_contours(topo_json) for topo_json in topo_jsons
    ]

    # create closed contours
    bbox_list = [
        _data.GetLayerByName(TOPO_LAYER_NAME).GetExtent()
        for _data in data
    ]

    closed_lines_by_elevation_list = []
    for bbox, lbe in zip(bbox_list, lines_by_elevation_list):
        
        ccomb = ContourCombiner(bbox, eps=1e-6)
        combined_lbe = ccomb.combine_contours(lbe)
        
        cclose = ContourCloser(bbox)
        closed_lbe = {}
        for elevation, lines in combined_lbe.items():
            closed_lines = []
            for line in lines:
                closed_line = cclose.close_contour(line)
                
                if cclose.error:
                    import matplotlib.pyplot as plt
                    plt.figure('contour test')
                    plt.plot(
                        [bbox[0], bbox[0], bbox[1], bbox[1]],
                        [bbox[2], bbox[3], bbox[3], bbox[2]],
                        'k'
                    )
                    x, y, _ = [list(l) for l in zip(*closed_line)]
                    plt.plot(x, y, 'g')
                    x, y, _ = [list(l) for l in zip(*line)]
                    plt.plot(x, y, 'r')
                    plt.show()
                    
                closed_lines.append(closed_line)
            closed_lbe[elevation] = closed_lines
        closed_lines_by_elevation_list.append(closed_lbe)

    def combine_dicts(dict_list):
        out_dict = collections.defaultdict(list)
        for d in dict_list:
            for k, v in d.items():
                out_dict[k].extend(v)
        return out_dict

    lines_by_elevation = combine_dicts(closed_lines_by_elevation_list)
        
    # this layer comes with extent information that we can use when
    # defining the svg
    lat_min, lat_max, lon_min, lon_max = extents(data, TOPO_LAYER_NAME)
    lat_center = (lat_max + lat_min) / 2.0
    lon_center = (lon_max + lon_min) / 2.0
    print(f"center: {lat_center}, {lon_center}")
    aspect_ratio = 1 / math.cos(math.radians(lat_center))
    # aspect_ratio = 1.0

    def xfrm_pts(points):
        return list(itertools.chain(
            *[(lat, aspect_ratio*lon) for lat, lon in points]
        ))
    
    # Get water features
    water_json = list(itertools.chain(*[
        extract_layer_features(_data, WATER_LAYER_NAME) for _data in data
    ]))

    # get water geometry
    water_geometry = list(itertools.chain(*[
        w["geometry"]["coordinates"][0] for w in water_json
    ]))

    # Now create the SVG image

    # sort the lines by elevation so we draw them in the right order
    sorted_lines = list(
        sorted(lines_by_elevation.items(), key=lambda x: x[0])
    )
    sorted_lines = [
        [(elev, [(pt.lon, pt.lat) for pt in line.points]) for line in lines]
        for elev, lines in sorted_lines
    ]
    sorted_lines = list(itertools.chain(*sorted_lines))

    elevations = list(sorted(set(lines_by_elevation.keys())))
    min_elev, max_elev = elevations[0], elevations[-1]
    # remember we're working with coordinates in degrees, so the pixel
    # scale is very large and stroke width needs to be very small
    PIXEL_SCALE = 10000
    STROKE_WIDTH = 1.0 / PIXEL_SCALE
    STROKE_COLOR_MIN = (0, 64, 0)
    STROKE_COLOR_MAX = (0, 255, 0)
    d = draw.Drawing(
        *xfrm_pts([(lon_max-lon_min, lat_max-lat_min)]),
        origin=[*xfrm_pts([(lon_min, lat_min)])],
        displayInline=False
    )

    for water in water_geometry:
        linepoints = [(pt[0], pt[1]) for pt in water]
        d.append(
            draw.Lines(
                *xfrm_pts(linepoints),
                close=True,
                stroke_width=STROKE_WIDTH,
                fill='#4488ff',
                stroke='#4488ff',
            )
        )
        
    for elev, line in sorted_lines:
        norm_cval = elev/(max_elev-min_elev)
        d.append(
            draw.Lines(
                *xfrm_pts(line),
                close=False,
                stroke_width=STROKE_WIDTH,
                fill='none',
                # fill='#eeeeee',
                stroke=interpolate_color(
                    STROKE_COLOR_MIN, STROKE_COLOR_MAX, norm_cval
                )
            )
        )

    # add test route
    with open("routes.json") as fp:
        routes = json.load(fp)
    for route in routes:
        linepoints = [(pt[1], pt[0]) for pt in route]
        d.append(draw.Lines(
            *xfrm_pts(linepoints),
            close=False,
            stroke_width=3*STROKE_WIDTH,
            opacity=0.5,
            fill='none',
            # fill='#eeeeee',
            stroke="#FF4444",
        ))

    d.setPixelScale(PIXEL_SCALE)  # Set number of pixels per geometry unit
    # d.setRenderSize(400,200)  # Alternative to setPixelScale
    d.saveSvg('contours.svg')
