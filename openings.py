from seg import *
import numpy as np
from shapely.geometry import Polygon, LineString
def wall_ends(walls,minw=1.5,maxw=10):
    ends=[]
    for pg in (walls.geoms if hasattr(walls,"geoms") else [walls]):
        pg=pg.simplify(0.25)
        rings=[pg.exterior]+list(pg.interiors)
        for ring in rings:
            c=np.array(ring.coords)[:-1]; n=len(c)
            for i in range(n):
                a,b=c[i],c[(i+1)%n]; L=np.linalg.norm(b-a)
                if not(minw<=L<=maxw): continue
                pa,nb=c[i-1],c[(i+2)%n]
                u=(b-a)/L; d1=a-pa; d2=nb-b
                if np.linalg.norm(d1)<2*L or np.linalg.norm(d2)<2*L: continue
                d1/=np.linalg.norm(d1); d2/=np.linalg.norm(d2)
                if abs(d1@u)>.1 or abs(d2@u)>.1 or d1@d2>-0.9: continue
                nrm=np.array([u[1],-u[0]]); mid=(a+b)/2
                if pg.contains(Point(*(mid+nrm*0.5))): nrm=-nrm
                ends.append(dict(a=a,b=b,mid=mid,n=nrm,w=L))
    return ends
def pair_openings(ends,gmin=6,gmax=45):
    out=[];used=set()
    cand=[]
    for i,e in enumerate(ends):
        for j,f in enumerate(ends):
            if j<=i: continue
            if e["n"]@f["n"]>-0.95: continue
            v=f["mid"]-e["mid"]; dist=v@e["n"]
            lat=np.linalg.norm(v-dist*e["n"])
            if gmin<=dist<=gmax and lat<1.5: cand.append((dist,i,j))
    for dist,i,j in sorted(cand):
        if i in used or j in used: continue
        used|={i,j}; e,f=ends[i],ends[j]
        out.append(dict(seg=LineString([e["mid"],f["mid"]]),quad=Polygon([e["a"],e["b"],f["a"],f["b"]]).convex_hull,width_pt=dist))
    return out
ends=wall_ends(walls); ops=pair_openings(ends)
for o in ops:
    o["door"]=next((k for k,dd in enumerate(doors) if dd["thr"].buffer(3).intersects(o["seg"].centroid)),None)
if __name__=="__main__":
    print(len(ends),"wall ends;",len(ops),"openings")
    for o in ops: print(round(o["width_pt"],1),[round(v) for v in o["seg"].centroid.coords[0]],"door" if o["door"] is not None else "open")
