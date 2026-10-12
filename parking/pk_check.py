from pk_base import *
import cv2
from skimage.morphology import skeletonize
drive=unary_union([q for x in dr if x.get("layer")=="0" and x.get("fill") and abs(x["fill"][0]-.88)<.01 for q in map(D,as_polys(x))]).buffer(0.3).buffer(-0.3)
obst=unary_union(layer_polys("A-COLUMN HATCH")+layer_polys("A-COLUMN-RCC")+layer_polys("RCC COLUMN T1")+[l.buffer(0.6) for l in layer_lines("WALL")+layer_lines("A-WALL-MAS")])
clear=drive.difference(obst)
# bays
bays=[]
for x in dr:
    if x.get("layer")!="A-PARKING": continue
    for q in as_polys(x):
        q=D(q); rr=q.minimum_rotated_rectangle
        if q.area/rr.area<0.97: continue
        xs=np.array(rr.exterior.coords); e=[np.linalg.norm(xs[i+1]-xs[i]) for i in range(4)]
        a,b=sorted(e[:2])
        if 13<a<16 and 27<b<31:
            col=x.get("color"); tandem=max(col)<0.05
            bays.append(dict(poly=q,w=a*S_M,l=b*S_M,tandem=tandem,xs=xs))
# raster for clear width
S=6.0; X0,Y0,X1,Y1=[v for v in drive.bounds]; X0-=5;Y0-=5;X1+=5;Y1+=5
W,H=int((X1-X0)*S),int((Y1-Y0)*S)
def px(c): return np.array([[(x-X0)*S,(y-Y0)*S] for x,y in c],np.int32)
mask=np.zeros((H,W),np.uint8)
for g in (clear.geoms if hasattr(clear,"geoms") else [clear]):
    cv2.fillPoly(mask,[px(g.exterior.coords)],1)
    for h in g.interiors: cv2.fillPoly(mask,[px(h.coords)],0)
dt=cv2.distanceTransform(mask,cv2.DIST_L2,5)/S*S_M*2   # local clear width (m) = 2*dist to edge
sk=skeletonize(mask>0)
# prune skeleton tips: ignore skeleton px whose local width < 1.0 m within 2 m of a tip (dead-end corners)
wvals=dt[sk]
if __name__=="__main__":
    print("bays",len(bays),"tandem",sum(b["tandem"] for b in bays))
    ws=np.array([b["w"] for b in bays]); ls=np.array([b["l"] for b in bays])
    print("bay width m: min %.2f median %.2f max %.2f | length: min %.2f median %.2f max %.2f"%(ws.min(),np.median(ws),ws.max(),ls.min(),np.median(ls),ls.max()))
    print("drive clear area m2 %.0f"%(clear.area*S_M**2))
    print("skeleton width percentiles (m):",np.round(np.percentile(wvals,[1,5,10,25,50]),2))
from scipy.ndimage import convolve, label
def prune(sk,n):
    sk=sk.copy().astype(np.uint8); k=np.ones((3,3),np.uint8); k[1,1]=0
    for _ in range(n):
        nb=convolve(sk,k,mode="constant")
        ends=(sk==1)&(nb<=1)
        if not ends.any(): break
        sk[ends]=0
    return sk.astype(bool)
core=prune(sk,int(4.0/(S_M/S)))     # remove spurs shorter than ~4 m
cw=dt[core]
# bottlenecks: connected runs of skeleton with width < 5.5 m
lab_,n_=label(core&(dt<5.5),structure=np.ones((3,3)))
necks=[]
for i in range(1,n_+1):
    ys,xs=np.where(lab_==i)
    if len(ys)<int(0.5/(S_M/S)): continue
    j=np.argmin(dt[ys,xs]); necks.append(dict(w=float(dt[ys[j],xs[j]]),pt=(xs[j]/S+X0,ys[j]/S+Y0),len_m=len(ys)*S_M/S))
# bay access: front short edge touching drive (or tandem partner)
for b in bays:
    xs_=b["xs"]; edges=[LineString([xs_[i],xs_[i+1]]) for i in range(4)]
    short=[e for e in edges if e.length<20]
    b["front"]=any(e.distance(drive)<4.0 and e.buffer(4.0).intersection(drive).area>0.25*e.length*8 for e in short)
for b in bays:
    if not b["front"] and b["tandem"]:
        b["via"]=[o for o in bays if o is not b and o["front"] and o["poly"].distance(b["poly"])<1.0 and o["tandem"]]
if __name__=="__main__":
    print("pruned skeleton width percentiles (m):",np.round(np.percentile(cw,[0,1,5,25,50]),2))
    for nk in sorted(necks,key=lambda z:z["w"]): print("narrowing %.2f m over %.1f m at"%(nk["w"],nk["len_m"]),[round(v) for v in nk["pt"]])
    print("bays with direct aisle frontage",sum(b["front"] for b in bays),"; tandem rear via partner",sum(1 for b in bays if not b["front"] and b.get("via")),"; no access",[ [round(v) for v in b["poly"].centroid.coords[0]] for b in bays if not b["front"] and not b.get("via")])
