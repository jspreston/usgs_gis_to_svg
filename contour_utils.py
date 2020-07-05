"""
This assumes that points are in (lat, lon) order!!
"""
import math
from dataclasses import dataclass


EDGE_ORDER = ["N", "W", "S", "E"]
EDGE_IDX = {edge: idx for idx, edge in enumerate(EDGE_ORDER)}
EDGE_WINDING_DIR = {"N": -1, "W": -1, "S": 1, "E": 1}

@dataclass
class Pt:
    lat: float
    lon: float


def winding_dir_order(edge, pt_start, pt_end):
    """
    for pt_start and pt_end both on edge 'edge' return 1 if end is
    after start in winding direction, else -1
    """
    if edge in {"N", "S"}:
        coord_start = pt_start.lon
        coord_end = pt_end.lon
    elif edge in {"E", "W"}:
        coord_start = pt_start.lat
        coord_end = pt_end.lat
    else:
        raise ValueError(f"unrecognized edge {edge}")

    sign = coord_end - coord_start
    sign /= abs(sign)
    sign *= EDGE_WINDING_DIR[edge]

    return sign


def get_next_edge(cur_edge):
    cur_edge_idx = EDGE_IDX[cur_edge]
    next_edge = EDGE_ORDER[(cur_edge_idx + 1) % 4]  # next edge, wrapped
    return next_edge

def convert_to_pts(line):
    return [Pt(lat=pt[1], lon=pt[0]) for pt in line]

def convert_from_pts(pt_line):
    return [(pt.lon, pt.lat, 0.0) for pt in pt_line]



class ContourCloser:

    def __init__(self, bbox, eps=1e-6):
        """
        bbox should be [lat_min, lat_max, lon_min, lon_max]
        """
        self.lon_min = bbox[0]
        self.lon_max = bbox[1]
        self.lat_min = bbox[2]
        self.lat_max = bbox[3]
        self.eps = eps

    
    def pt_equals(self, pt_a, pt_b):
        dist = math.sqrt((pt_a.lat-pt_b.lat)**2 + (pt_a.lon-pt_b.lon)**2)
        return abs(dist) < self.eps

    def get_point_edge(self, pt):
        if abs(pt.lat-self.lat_max) < self.eps:
            return "N"
        if abs(pt.lat-self.lat_min) < self.eps:
            return "S"
        if abs(pt.lon-self.lon_min) < self.eps:
            return "W"
        if abs(pt.lon-self.lon_max) < self.eps:
            return "E"
        raise ValueError(
            f"point {pt.lat, pt.lon} not within {self.eps} tolerance of "
            f"bbox edges [{self.lat_min}, {self.lat_max}, {self.lon_min}, {self.lon_max}]"
        )

    def next_bb_corner(self, cur_edge):
        if cur_edge == "N":
            return Pt(lat=self.lat_max, lon=self.lon_min)
        elif cur_edge == "W":
            return Pt(lat=self.lat_min, lon=self.lon_min)
        elif cur_edge == "S":
            return Pt(lat=self.lat_min, lon=self.lon_max)
        elif cur_edge == "E":
            return Pt(lat=self.lat_max, lon=self.lon_max)
        else:
            raise ValueError(f"unrecognized edge {edge}")
        
    def close_contour(self, line):
        print(f"line has {len(line)} points")
        points = convert_to_pts(line)
        points = self._close_contour(points)
        line = convert_from_pts(points)
        print(f"final line has {len(line)} points")
        return line
    
    def _close_contour(self, points):
        
        first_point = points[0]
        last_point = points[-1]

        if self.pt_equals(first_point, last_point):
            # it's already closed, nothing to do
            print("already closed!")
            return points

        first_point_edge = self.get_point_edge(first_point)
        last_point_edge = self.get_point_edge(last_point)

        if last_point_edge == first_point_edge:
            if winding_dir_order(first_point_edge, last_point, first_point):
                print("closing immediately")
                # just close the contour directly to start
                points = points + [first_point]
                return points
            
        # otherwise we need to move to the next corner
        cur_edge = last_point_edge
        print(f"adding initial corner point (end of {cur_edge} edge)")
        next_edge = get_next_edge(cur_edge)
        points = points + [self.next_bb_corner(cur_edge)]

        while True:
            # we've come aroud to the first point, just close the contour
            if cur_edge == first_point_edge:
                print(f"found final point (on {cur_edge} edge), closing and finishing")
                points = points + [first_point]
                return points
            # add the corner and keep going
            print(f"adding corner point (end of {cur_edge} edge)")
            points = points + [self.next_bb_corner(cur_edge)]
            cur_edge = get_next_edge(cur_edge)
