from seg import *
from openings import ops
import numpy as np, cv2
from shapely.geometry import Polygon
S=4.0  # px per pt
X0,Y0,X1,Y1=140,190,480,620
W,H=int((X1-X0)*S),int((Y1-Y0)*S)
def to_px(coords): return np.array([[(x-X0)*S,(y-Y0)*S] for x,y in coords],np.int32)
def draw_poly(img,g,val):
    for pg in (g.geoms if hasattr(g,"geoms") else [g]):
        if pg.geom_type!="Polygon" or pg.is_empty: continue
        cv2.fillPoly(img,[to_px(pg.exterior.coords)],val)
        for h in pg.interiors: cv2.fillPoly(img,[to_px(h.coords)],0 if val else 1)
def draw_line(img,ls,val,th):
    for g in (ls.geoms if hasattr(ls,"geoms") else [ls]):
        cv2.polylines(img,[to_px(g.coords)],False,val,th)
walllines=unary_union([l for x in dr if x.get("layer")=="WALL" for l in as_lines(x)])
winlines=unary_union([l for x in dr if x.get("layer") in("A-WINDOWS","A-WINDOW") for l in as_lines(x)])
floor=np.zeros((H,W),np.uint8); draw_poly(floor,blue,1); deck=np.zeros((H,W),np.uint8); draw_poly(deck,tan,1)
barrier=np.zeros((H,W),np.uint8)
draw_poly(barrier,walls,1); draw_line(barrier,walllines,1,3); draw_line(barrier,winlines,1,3)
def extend(ls,e=4.0):
    (x0,y0),(x1,y1)=ls.coords[0],ls.coords[-1]; v=np.array([x1-x0,y1-y0]); v/=np.linalg.norm(v)
    return LineString([np.array([x0,y0])-v*e,np.array([x1,y1])+v*e])
for dd in doors: dd["thr_ext"]=extend(dd["thr"]); draw_line(barrier,dd["thr_ext"],1,3)
for o in ops: draw_poly(barrier,o["quad"].buffer(0.3),1); draw_line(barrier,o["seg"],1,3)
free=((floor|deck)&(1-barrier)).astype(np.uint8)
# separate floor vs deck by material too
lab_f=cv2.connectedComponents(free&floor&(1-deck),connectivity=4)[1]
lab_d=cv2.connectedComponents(free&deck,connectivity=4)[1]
comps=[]
for L,kind in ((lab_f,"floor"),(lab_d,"deck")):
    for i in range(1,L.max()+1):
        m=(L==i).astype(np.uint8)
        if m.sum()<S*S*20: continue
        cs,_=cv2.findContours(m,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        c=max(cs,key=cv2.contourArea)
        pg=Polygon([(x/S+X0,y/S+Y0) for x,y in c[:,0,:]]).buffer(0)
        comps.append(dict(kind=kind,mask=m,poly=pg))
if __name__=="__main__":
    print(len(comps),"rooms", sorted([round(c["poly"].area) for c in comps],reverse=True))
    vis=np.full((H,W,3),255,np.uint8)
    rng=np.random.default_rng(1)
    for c in comps: vis[c["mask"]>0]=rng.integers(80,230,3)
    vis[barrier>0]=0
    for t,r in lab:
        cx,cy=(r.x0+r.x1)/2,(r.y0+r.y1)/2
        if X0<cx<X1 and Y0<cy<Y1: cv2.circle(vis,(int((cx-X0)*S),int((cy-Y0)*S)),3,(255,0,0),-1)
    cv2.imwrite("rcells.png",cv2.resize(vis,None,fx=.5,fy=.5))
