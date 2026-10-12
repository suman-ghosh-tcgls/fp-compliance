import sys; sys.path.insert(0,".."); import os
from geom import *
from shapely.geometry import Point, LineString, box
from shapely.ops import unary_union
import collections
PARKING_PDF=os.environ.get("PARKING_PDF",os.path.join(INPUTS,"2026.09.23_TOWER Q - PARKING FLOOR PLANS-Model.pdf"))
d=fitz.open(PARKING_PDF); p=d[0]; RM=p.rotation_matrix
dr=p.get_drawings()   # coords in display space? -> force unrotated then map
p.set_rotation(0); dr=p.get_drawings()
def D(g):   # unrotated geometry -> display geometry
    from shapely import affinity
    a,b,c,dd,e,f=RM.a,RM.b,RM.c,RM.d,RM.e,RM.f
    return affinity.affine_transform(g,[a,c,b,dd,e,f])
S_M=2.76/16.2   # m per pt from lift-lobby dimension (RERA AREA layer)
def layer_polys(L,filled=None): return [D(q) for x in dr if x.get("layer")==L and (filled is None or bool(x.get("fill"))==filled) for q in as_polys(x)]
def layer_lines(L): return [D(l) for x in dr if x.get("layer")==L for l in as_lines(x)]
