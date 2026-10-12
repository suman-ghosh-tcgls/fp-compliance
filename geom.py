import pymupdf as fitz, warnings, numpy as np; warnings.filterwarnings("ignore")
from shapely.geometry import Polygon, LineString, MultiPolygon
from shapely.ops import unary_union
import os
INPUTS=os.path.join(os.path.dirname(os.path.abspath(__file__)),"inputs")
OUTPUTS=os.path.join(os.path.dirname(os.path.abspath(__file__)),"outputs"); os.makedirs(OUTPUTS,exist_ok=True)
PDF=os.environ.get("FLOORPLAN_PDF",os.path.join(INPUTS,"2028.09.23_TOWER Q_UNIT PLANS-Model-5.pdf"))
def load():
    d=fitz.open(PDF); p=d[0]; p.set_rotation(0); return d,p
def subpaths(x):
    """yield point lists (closed rings or polylines) from a pymupdf drawing"""
    cur=[]
    for it in x["items"]:
        k=it[0]
        if k=="re":
            r=it[1]; yield [(r.x0,r.y0),(r.x1,r.y0),(r.x1,r.y1),(r.x0,r.y1)],True; continue
        if k=="qu":
            q=it[1]; yield [tuple(q.ul),tuple(q.ur),tuple(q.lr),tuple(q.ll)],True; continue
        a=tuple(it[1]); b=tuple(it[-1])
        if k=="c":
            pts=[np.array(tuple(q)) for q in it[1:5]]
            seg=[tuple(((1-t)**3)*pts[0]+3*((1-t)**2)*t*pts[1]+3*(1-t)*t*t*pts[2]+t**3*pts[3]) for t in [i/8 for i in range(9)]]
        else: seg=[a,b]
        if cur and (abs(cur[-1][0]-seg[0][0])>1e-3 or abs(cur[-1][1]-seg[0][1])>1e-3):
            yield cur,False; cur=[]
        cur+= seg if not cur else seg[1:]
    if cur: yield cur,False
def as_polys(x):
    out=[]
    for pts,closed in subpaths(x):
        if len(pts)>=3:
            pg=Polygon(pts).buffer(0)
            if pg.area>1e-3: out.append(pg)
    return out
def as_lines(x):
    return [LineString(pts) for pts,_ in subpaths(x) if len(pts)>=2]
