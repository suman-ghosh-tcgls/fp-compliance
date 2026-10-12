from rseg import *
import re
# room labels: name line followed by "a x b" metric line
DIM=re.compile(r"^(\d+\.\d+)\s*[xX]\s*(\d+\.\d+)$")
lines=[(t,r) for t,r in lab]
names=[]
for i,(t,r) in enumerate(lines):
    if DIM.match(t) or "'" in t or not t[0].isalpha(): continue
    # find nearest dim line just "below" in reading order (here: smaller x since text is rotated)
    best=None
    for t2,r2 in lines:
        m=DIM.match(t2)
        if not m: continue
        dx=r.x0-r2.x1; dy=abs((r.y0+r.y1)/2-(r2.y0+r2.y1)/2)
        if -1<dx<14 and dy<8 and (best is None or dx<best[0]): best=(dx,m,r2)
    if best: names.append([t,r,(float(best[1].group(1)),float(best[1].group(2)))])
# merge two-line names (e.g. "Servant"/"Room", "Common"/"Toilet")
merged=[]
for t,r in lines:
    pass
nm={}
for t,r,dim in names:
    nm.setdefault(dim,[]).append((t,r))
labels=[]
for dim,v in nm.items():
    v.sort(key=lambda z:-z[1].x0)  # rotated text: larger x = earlier line
    labels.append(dict(name=" ".join(t for t,_ in v),pt=((v[0][1].x0+v[-1][1].x1)/2,(v[0][1].y0+v[0][1].y1)/2),dim=dim))
# id raster
idimg=np.zeros((H,W),np.int32)
for k,c in enumerate(comps): idimg[c["mask"]>0]=k+1
def cell_at(x,y,r=3):
    px,py=int((x-X0)*S),int((y-Y0)*S)
    win=idimg[max(py-int(r*S),0):py+int(r*S)+1,max(px-int(r*S),0):px+int(r*S)+1]
    v=win[win>0]
    return int(np.bincount(v).argmax())-1 if v.size else None
for L in labels: L["cell"]=cell_at(*L["pt"],r=6)
for k,c in enumerate(comps):
    c["labels"]=[L for L in labels if L["cell"]==k]
    rr=c["poly"].minimum_rotated_rectangle; xs=np.array(rr.exterior.coords)
    e=sorted([np.linalg.norm(xs[1]-xs[0]),np.linalg.norm(xs[2]-xs[1])])
    c["obb"]=e
    c["inscribed_pt"]=2*cv2.distanceTransform((c["mask"]>0).astype(np.uint8),cv2.DIST_L2,5).max()/S
# scale: single-label near-rectangular cells
ratios=[]
for c in comps:
    if len(c["labels"])==1 and c["poly"].area/(c["obb"][0]*c["obb"][1])>0.93:
        a,b=sorted(c["labels"][0]["dim"]); ratios+= [a/c["obb"][0], b/c["obb"][1]]
M_PER_PT=float(np.median(ratios))
if __name__=="__main__":
    print("labels:",[(L["name"],L["dim"],L["cell"]) for L in labels])
    print("scale m/pt",round(M_PER_PT,5),"-> 1:%d"%round(M_PER_PT/0.000352778),"spread",np.round(np.percentile(ratios,[10,90]),5))
    for k,c in enumerate(comps):
        if c["poly"].area<50: continue
        print(k,c["kind"],[L["name"] for L in c["labels"]],round(c["poly"].area*M_PER_PT**2,2),"m2 obb",[round(v*M_PER_PT,2) for v in c["obb"]])
