"""
This assumes that points are in (lat, lon) order!!
"""
import math
from dataclasses import dataclass
from typing import List

import more_itertools
import numpy as np
import matplotlib.pyplot as plt


EDGE_ORDER = ["N", "W", "S", "E"]
EDGE_IDX = {edge: idx for idx, edge in enumerate(EDGE_ORDER)}
EDGE_WINDING_DIR = {"N": -1, "W": -1, "S": 1, "E": 1}


@dataclass
class Pt:
    lat: float
    lon: float

    def dist_to(self, other_pt):
        return math.sqrt(
            (self.lat-other_pt.lat)**2 + (self.lon-other_pt.lon)**2
        )


@dataclass
class Contour:
    id: str
    dataset_id: str
    elevation: float
    points: List[Pt]


def plot_line(line, **kwargs):
    x, y = [list(coords) for coords in zip(*[(pt.lon, pt.lat) for pt in line])]
    plt.plot(x, y, **kwargs)


def debug_plot(lines):
    colors = ['r', 'g', 'b', 'c', 'y', 'm', 'orange', 'turquoise', 'violet', 'deeppink']
    for lidx, line in enumerate(lines):
        c = colors[lidx % len(colors)]
        plot_line(line, color=c)
        jitter = 1e-4*np.random.rand(2)

        pt = line[0]
        plt.scatter([pt.lon+jitter[0]], [pt.lat+jitter[1]], marker='o', color=c)
        plt.text(pt.lon+jitter[0], pt.lat+jitter[1], f"{lidx}", {"color": c})

        pt = line[-1]
        plt.scatter([pt.lon+jitter[0]], [pt.lat+jitter[1]], marker='x', color=c)


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


class ContourBase:
    
    def __init__(self, bbox, eps=1e-6):
        """
        bbox should be [lat_min, lat_max, lon_min, lon_max]
        """
        self.lon_min = bbox[0]
        self.lon_max = bbox[1]
        self.lat_min = bbox[2]
        self.lat_max = bbox[3]
        self.eps = eps
        self.error = None

    def pt_equals(self, pt_a, pt_b):
        dist = pt_a.dist_to(pt_b)
        return abs(dist) < self.eps

    def is_edge_point(self, pt):
        try:
            self.get_point_edge(pt)
            return True
        except ValueError:
            pass
        return False
    
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

    
class ContourCombiner(ContourBase):

    def __init__(self, bbox, eps=1e-6):
        super().__init__(bbox, eps)

    def combine_contours(self, contours_by_elevation):
        combined_contours_by_elevation = {}
        for elevation, contours in contours_by_elevation.items():
            contour_lines = [convert_to_pts(line) for line in contours]
            combined_contour_lines = self._combine_contours(contour_lines)
            combined_contours = [
                convert_from_pts(line) for line in combined_contour_lines
            ]
            combined_contours_by_elevation[elevation] = combined_contours
        return combined_contours_by_elevation

    def is_valid_contour(self, line):
        return (
            self.pt_equals(line[0], line[-1]) or
            (self.is_edge_point(line[0]) and self.is_edge_point(line[-1]))
        )

    def _combine_contours(self, contour_list):
        print(f"number of contours before combining: {len(contour_list)}")
        incomplete_contour_list, complete_contour_list = [
            list(l) for l in
            more_itertools.partition(self.is_valid_contour, contour_list)
        ]
        while incomplete_contour_list:
            # get a line to find matches for
            cur_line = incomplete_contour_list.pop()
            # now search the rest of the list, extending the contour
            # as much as possible
            while incomplete_contour_list:
                # if we've completed the contour, stop
                if self.is_valid_contour(cur_line):
                    break
                # see if we can extend the beginning of the contour
                if not self.is_edge_point(cur_line[0]):
                    dists = np.array([
                        cur_line[0].dist_to(candidate[-1])
                        for candidate in incomplete_contour_list
                    ])
                    best_match_idx = np.argmin(dists)
                    best_match_dist = dists[best_match_idx]
                    if best_match_dist > 1e-6:
                        print(f"WARNING: best match dist is {best_match_dist}")
                    extension = incomplete_contour_list[best_match_idx]
                    cur_line = extension + cur_line
                    del incomplete_contour_list[best_match_idx]
                    continue
                # see if we can extend the end of the contour
                if not self.is_edge_point(cur_line[-1]):
                    dists = np.array([
                        cur_line[-1].dist_to(candidate[0])
                        for candidate in incomplete_contour_list
                    ])
                    best_match_idx = np.argmin(dists)
                    best_match_dist = dists[best_match_idx]
                    if best_match_dist > 1e-6:
                        print(f"WARNING: best match dist is {best_match_dist}")
                    extension = incomplete_contour_list[best_match_idx]
                    cur_line = cur_line + extension
                    del incomplete_contour_list[best_match_idx]
                    continue
                raise ValueError("Impossible, we can't get here!")

            if not self.is_valid_contour(cur_line):
                plt.plot()
                debug_plot(contour_list)
                plot_line(cur_line, lw=2, ls=":", color='r')
                plt.show()
                raise ValueError("Found contour that could not be completed!")

            complete_contour_list.append(cur_line)

        print(f"number of contours after combining: {len(complete_contour_list)}")
        return complete_contour_list


class ContourCloser(ContourBase):

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
            raise ValueError(f"unrecognized edge {cur_edge}")

    def fix_bad_point(self, point, endpoint):
        
        n_dist = abs(point.lat - self.lat_max)
        w_dist = abs(point.lon - self.lon_min)
        s_dist = abs(point.lat - self.lat_min)
        e_dist = abs(point.lon - self.lon_max)
        pt_dist = point.dist_to(endpoint)
        distances = np.array([n_dist, w_dist, s_dist, e_dist, pt_dist])
        idx = np.argmin(distances)
        if idx == 0:  # N
            return Pt(lat=self.lat_max, lon=point.lon), True
        elif idx == 1:  # W
            return Pt(lat=point.lat, lon=self.lon_min), True
        elif idx == 2:  # S
            return Pt(lat=self.lat_min, lon=point.lon), True
        elif idx == 3:  # E
            return Pt(lat=point.lat, lon=self.lon_max), True
        elif idx == 4:
            return endpoint, False
        raise ValueError(f"huh? unknown idx {idx}")
    
    def close_contour(self, line):
        self.error = False
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

        # we have to fix some contours that seem like they should end
        # on a map boundary but don't quite touch the edge
        try:
            first_point_edge = self.get_point_edge(first_point)
        except ValueError:
            print("fixing bad first point")
            self.error = True
            first_point, is_boundary = self.fix_bad_point(first_point, last_point)
            points = [first_point] + points
            if not is_boundary:
                return points  # fixing closed boundary
            first_point_edge = self.get_point_edge(first_point)
            
        try:
            last_point_edge = self.get_point_edge(last_point)
        except ValueError:
            print("fixing bad last point")
            self.error = True
            last_point, is_boundary = self.fix_bad_point(last_point, first_point)
            points = points + [last_point]
            if not is_boundary:
                return points  # fixing closed boundary
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
