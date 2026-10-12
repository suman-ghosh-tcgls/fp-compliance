from geom import *
from shapely.geometry import Point, LineString, box
from shapely.ops import unary_union
import numpy as np
d,p=load(); dr=p.get_drawings()
def fills(layers,pred):
    return unary_union([q for x in dr if x.get("layer") in layers and x.get("fill") and pred(x["fill"]) for q in as_polys(x)])
isblue=lambda f: abs(f[0]-.82)<.01 and abs(f[2]-1)<.01
istan =lambda f: abs(f[0]-.83)<.01 and abs(f[2]-.62)<.02
isblk =lambda f: max(f)<.05
blue=fills({"A-HATCH"},isblue); tan=fills({"A-HATCH"},istan)
walls=fills({"A-HATCH","A-COLUMN HATCH"},isblk)
# doors: arc + leaf -> hinge, threshold
leaves=[q for x in dr if x.get("layer")=="A_DOOR" and not any(i[0]=="c" for i in x["items"]) for q in as_polys(x) if max(q.bounds[2]-q.bounds[0],q.bounds[3]-q.bounds[1])>10]
doors=[]
for x in dr:
    if x.get("layer")!="A_DOOR" or not any(i[0]=="c" for i in x["items"]): continue
    pts=[pt for pts,_ in subpaths(x) for pt in pts]; E1=np.array(pts[0]);E2=np.array(pts[-1])
    best=None
    for C in (np.array([E1[0],E2[1]]),np.array([E2[0],E1[1]])):
        dl=min(Point(C).distance(l) for l in leaves)
        if best is None or dl<best[0]: best=(dl,C)
    C=best[1]
    # open endpoint = the one closer to a leaf's far end (leaf contains it)
    dE=[min(Point(E).distance(l) for l in leaves) for E in (E1,E2)]
    Eopen,Eclosed=(E1,E2) if dE[0]<dE[1] else (E2,E1)
    width=float(np.linalg.norm(Eclosed-C))
    doors.append(dict(hinge=C,closed=Eclosed,open=Eopen,width_pt=width,thr=LineString([C,Eclosed])))
def segment(region,doors,eps=0.6):
    cut=unary_union([dd["thr"] for dd in doors]).buffer(eps,cap_style=2)
    r=region.difference(walls).difference(cut)
    return [g for g in (r.geoms if hasattr(r,"geoms") else [r]) if g.area>5]
cells=[("floor",g) for g in segment(blue,doors)]+[("deck",g) for g in segment(tan,doors)]
# labels
lab=[]
for b in p.get_text("dict")["blocks"]:
    for l in b.get("lines",[]):
        t=" ".join(s["text"] for s in l["spans"]).strip()
        if t: lab.append((t,fitz.Rect(l["bbox"])))
if __name__=="__main__":
    print("walls comps",len(walls.geoms) if hasattr(walls,'geoms') else 1,"blue",round(blue.area),"tan",round(tan.area))
    print(len(doors),"doors widths(pt)",[round(dd["width_pt"],1) for dd in doors])
    print(len(cells),"cells",sorted([round(g.area) for _,g in cells],reverse=True))
    for t,r in lab: print(repr(t),[round(v) for v in r])
