"""
Create an output svg combining GIS data and Strava routes
"""
import json
import itertools
import os
import collections
import math
from typing import Any, Dict, List

from osgeo import gdal
import drawSvg as draw

import matplotlib.pyplot as plt

from contour_utils import ContourCloser, ContourCombiner, debug_plot
from contour_utils import Contour, Pt, Bbox, combine_bboxes

EPS = 1e-5

# just hard-code this for now
BASE_DIR = "/home/jsam/winHome/OneDrive - Microsoft/Documents/personal/topo_maps"
GIS_FILES = [
    # os.path.join(BASE_DIR, "VECTOR_Seattle_North_WA_7_5_Min_GDB.zip"),  # NE
    os.path.join(BASE_DIR, "VECTOR_Seattle_South_WA_7_5_Min_GDB.zip"),  # SE
    # os.path.join(BASE_DIR, "VECTOR_Shilshole_Bay_WA_7_5_Min_GDB.zip"),  # NW
    os.path.join(BASE_DIR, "VECTOR_Duwamish_Head_WA_7_5_Min_GDB.zip")  # SW
]
TOPO_LAYER_NAME = "Elev_Contour"
WATER_LAYER_NAME = "NHDWaterbody"

# There are occasional contour segments that are wound the wrong way.  This is super
# annoying, but I don't know an automatic way to detect them, so these were manually
# identified.
SEGMENTS_TO_FLIP = set([
    # these first two seem right
    "031508f3-89ca-43ee-8f98-aa1a43f849cc_206",
    "8b03d49b-0e59-4f7a-91f5-7efd4d25046b_216",
    #"cc2cf73d-6fdf-42e0-8e0b-7464c16bce20_99",  # not sure this one is right

    "8525de_15",
    "e964fb_16",
    "66eee2_102",
    "767ef7_118",
    "c2031c_1",
    # top of Duwamish Head
    "ab17e0_24",
    "efde8c_25",
    # bottom of shilshole bay
    "de2244_116",
    "58b248_86",
    "5ac4b4_13",
    "46ede7_117",
    "90c3ee_101",
    "a273d3_14",
    "a05b67_89",
    # Seattle South west
    "afbb6b_82",
    "aed65_150",
    "359cfc_101",
    "959b58_2",
    "8205f9_220",
    "4dad78_219",
    "359cfc_181",
    "b3fa7e_223",
    "4cdbb6_3",
    # "9bfb93_118",
    "bd4788_83",
    "9c6afb_153",
    "3e5f4a_85",
    "d0cf59_225",
    "d41db5_186",
    "63177_185",
    "57f876_115",




    # these are from combining plats
    # "1a098a3c-73b2-484e-83d0-f4d36cf173f9_221",
    # "9fdb7077-85e8-4093-b5dc-43bb17a25d82_196",
    # "1bdca8ad-5ab6-4d78-923b-ed76cb671510_172",
    # "7fcdf282-cfef-4f40-bf27-e583a0e7ba07_115",
    # "9630c4e6-efb9-4b2f-b1f8-b7add3a78e7b_7",
    # "19886904-4021-41ed-ba78-3899ac975fde_219",
    # "bb75a478-d7d6-4f68-a8b9-a20b134c8bab_117",
])


def _check_id(contour_id):
    for to_flip_id in SEGMENTS_TO_FLIP:
        if to_flip_id in contour_id:
            return True
    return False


def extract_layer_features(gis_data, layer_name):
    """
    Take GDAL data format and extract the layer features as JSON
    """
    layer = gis_data.GetLayerByName(layer_name)
    n_features = layer.GetFeatureCount()
    features = [layer.GetFeature(idx) for idx in range(1, n_features+1)]
    features_json = [json.loads(f.ExportToJson()) for f in features]
    return features_json


def get_topo_contours(topo_features_json) -> Dict[int, List[Contour]]:
    """Convert JSON topographic contours into Contour objects"""
    topo_lines = collections.defaultdict(list)
    # collect lines by elevation
    for f in topo_features_json:
        props = f["properties"]
        elevation = props["ContourElevation"]
        # it turns out that we can have segments with duplicate Permanent_Identifier
        # IDs, so we append the order index to deduplicate.
        id = props["Permanent_Identifier"] + "_" + str(f["id"])
        line = f['geometry']['coordinates'][0]
        points = [Pt(lat=pt[1], lon=pt[0]) for pt in line]
        contour = Contour(id=id, elevation=elevation, points=points)
        if _check_id(contour.id):  # should we flip it?
            print(f"flipping segment {contour.id}")
            contour.reverse()
        topo_lines[elevation].append(contour)
    return dict(topo_lines)


def extents(gis_data, layer_name) -> Bbox:
    """Get the bounding box of the given layer"""
    lon_min, lon_max, lat_min, lat_max = gis_data.GetLayerByName(layer_name).GetExtent()
    return Bbox(lon_min=lon_min, lon_max=lon_max, lat_min=lat_min, lat_max=lat_max)


def interpolate_color(cmin, cmax, cval):
    cval = [
        channel_min*(1.0-cval) + channel_max*cval
        for channel_min, channel_max in zip(cmin, cmax)
    ]
    return f"rgb({int(cval[0])}, {int(cval[1])}, {int(cval[2])})"


# gdal python wrappers don't raise exceptions by default
gdal.UseExceptions()


if __name__ == "__main__":

    print("Reading GIS files...")
    data = [gdal.ogr.Open(fname) for fname in GIS_FILES]
    if not data:
        raise ValueError("No input data, were input GIS files found?")

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

    bbox_list = [extents(_data, TOPO_LAYER_NAME) for _data in data]
    # calculate the global bounding box
    bbox_full = combine_bboxes(bbox_list)

    # combine
    def combine_dicts(dict_list: List[Dict[Any, list]]) -> Dict[Any, list]:
        out_dict = collections.defaultdict(list)
        for d in dict_list:
            for k, v in d.items():
                out_dict[k].extend(v)
        return out_dict

    lines_by_elevation = combine_dicts(lines_by_elevation_list)
    ccomb = ContourCombiner(bbox_full, eps=EPS)
    combined_lbe = ccomb.combine_contours(lines_by_elevation)
    cclose = ContourCloser(bbox_full, eps=EPS)
    closed_lbe = cclose.close_contours(combined_lbe)

    #text_params = {"rotation": "vertical"}
    text_params = {}
    debug_plot(itertools.chain(*closed_lbe.values()), show_ids=True, text_params=text_params)
    plt.show()
    foo

    center = bbox_full.center()
    print(f"center: {center.lat}, {center.lon}")
    aspect_ratio = 1 / math.cos(math.radians(center.lat))
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

    # length of sides and lower-left corner
    bbox_sz = (bbox_full.lon_max-bbox_full.lon_min, bbox_full.lat_max-bbox_full.lat_min)
    bbox_origin = (bbox_full.lon_min, bbox_full.lat_min)
    d = draw.Drawing(
        *xfrm_pts([bbox_sz]),
        origin=[*xfrm_pts([bbox_origin])],
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
