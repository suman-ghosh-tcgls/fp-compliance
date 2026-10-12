from rooms import *
import networkx as nx, json
m=M_PER_PT
G=nx.MultiGraph()
keep=[k for k,c in enumerate(comps) if c["poly"].area*m*m>0.5]
def kind_of(names):
    s=" ".join(names).lower()
    if not names: return "circulation"
    if "toi" in s: return "toilet"
    if "bedroom" in s or "servant room" in s: return "bedroom"
    if "kitchen" in s: return "kitchen"
    if "living" in s or "dining" in s: return "living"
    if "deck" in s or "utility" in s: return "service_open"
    return "other"
for k in keep:
    c=comps[k]; names=[L["name"] for L in c["labels"]]
    G.add_node(k,name=" / ".join(names) or f"Passage {k}",kind=kind_of(names),
               area_m2=round(c["poly"].area*m*m,2),min_width_m=round(c["inscribed_pt"]*m,2),
               obb_m=[round(v*m,2) for v in c["obb"]],label_dims=[L["dim"] for L in c["labels"]])
G.add_node("EXT",name="Exterior",kind="exterior"); G.add_node("LOBBY",name="Common lobby",kind="exterior")
def sides(seg,off=5):
    (x0,y0),(x1,y1)=seg.coords[0],seg.coords[-1]; v=np.array([x1-x0,y1-y0]); v/=np.linalg.norm(v); n=np.array([-v[1],v[0]])
    mid=np.array(seg.interpolate(.5,normalized=True).coords[0])
    return [cell_at(*(mid+s*n*off),r=2) for s in (1,-1)]
# door edges
for i,dd in enumerate(doors):
    a,b=sides(dd["thr"])
    a=a if a in keep else "LOBBY"; b=b if b in keep else "LOBBY"
    if a!=b: G.add_edge(a,b,type="door",id=f"D{i}",width_m=round(dd["width_pt"]*m,2))
# doorless openings
for i,o in enumerate(ops):
    if o["door"] is not None: continue
    a,b=sides(o["seg"],off=6)
    if a in keep and b in keep and a!=b: G.add_edge(a,b,type="opening",id=f"O{i}",width_m=round(o["width_pt"]*m,2))
# wall adjacency: boundaries within one wall thickness of each other
polys={k:comps[k]["poly"] for k in keep}
for i in keep:
    for j in keep:
        if j<=i: continue
        ov=polys[i].buffer(4.5).intersection(polys[j].buffer(4.5))
        if ov.area>0:
            ln=ov.area/9.0*m
            if ln>0.3: G.add_edge(i,j,type="wall",shared_m=round(ln,2))
# glazing objects: window-layer lines + WALL-layer facade lines that are not inside wall poche
gl=[l for x in dr if x.get("layer") in("A-WINDOWS","A-WINDOW") for l in as_lines(x)]
wall_lines=[l.difference(walls.buffer(0.6)) for x in dr if x.get("layer")=="WALL" for l in as_lines(x)]
gl+=[g for l in wall_lines for g in (l.geoms if hasattr(l,"geoms") else [l]) if g.length>6]
wl=unary_union([l.buffer(1.5,cap_style=2) for l in gl])
wins=[]
for g in (wl.geoms if hasattr(wl,"geoms") else [wl]):
    xs=np.array(g.minimum_rotated_rectangle.exterior.coords)
    if min(np.linalg.norm(xs[1]-xs[0]),np.linalg.norm(xs[2]-xs[1]))<=5: wins.append(g); continue
    # blob of several elements: fall back to individual long straight lines
    for l in gl:
        if l.length>8 and l.within(g.buffer(0.1)): wins.append(l.buffer(1.5,cap_style=2))
env_full=unary_union([blue,tan,walls]).buffer(1.5).buffer(-1.5)
env_bdy=env_full.boundary   # outer facade + shaft voids
door_zone=unary_union([dd["thr_ext"].buffer(3) for dd in doors])
for wi,w in enumerate(wins):
    rr=w.minimum_rotated_rectangle; xs=np.array(rr.exterior.coords)
    e1,e2=xs[1]-xs[0],xs[2]-xs[1]; ax_=e1 if np.linalg.norm(e1)>np.linalg.norm(e2) else e2; L=np.linalg.norm(ax_)
    if L<8 or w.intersection(door_zone).area>0.5*w.area: continue
    n=np.array([-ax_[1],ax_[0]])/L; c=np.array(w.centroid.coords[0])
    sd=[]
    for sgn in (1,-1):
        hit=None
        for off in (3,5,8,12):
            hit=cell_at(*(c+sgn*n*off),r=1)
            if hit is not None: break
        sd.append(hit if hit in keep else None)
    a_,b_=sd
    if a_ is not None and b_ is not None and a_!=b_:
        if G.nodes[a_]["kind"]=="toilet" and G.nodes[b_]["kind"]=="toilet":
            G.add_edge(a_,"EXT",type="window",id=f"W{wi}",width_m=round(L*m,2),note="shaft ventilator",geom=w)
        else:
            G.add_edge(a_,b_,type="glazed_door",id=f"W{wi}",width_m=round(L*m,2),geom=w)
    elif (a_ is None)!=(b_ is None):
        G.add_edge(a_ if a_ is not None else b_,"EXT",type="window",id=f"W{wi}",width_m=round(L*m,2),geom=w)
# merge glazing per (pair,type): union geometry, one element per connected run
groups={}
for u,v,k,d in list(G.edges(keys=True,data=True)):
    if "geom" in d:
        groups.setdefault((frozenset((u,v)),d["type"]),[]).append(d["geom"]); G.remove_edge(u,v,k)
for (pair,t),gs in groups.items():
    u,v=tuple(pair) if len(pair)==2 else (next(iter(pair)),)*2
    U=unary_union([g.buffer(2.5) for g in gs])
    for gi,g in enumerate(U.geoms if hasattr(U,"geoms") else [U]):
        xs=np.array(g.minimum_rotated_rectangle.exterior.coords)
        L=max(np.linalg.norm(xs[1]-xs[0]),np.linalg.norm(xs[2]-xs[1]))-5
        G.add_edge(u,v,type=t,width_m=round(L*m,2),_geom=g)
# a second sash line of a sliding door can look like an exterior window: drop those
for u,v,k,d in list(G.edges(keys=True,data=True)):
    if d["type"]!="window": continue
    room=u if v=="EXT" else v
    if any(dd["type"]=="glazed_door" and dd["_geom"].distance(d["_geom"])<4 for nb in G[room] for dd in G[room][nb].values() if "_geom" in dd):
        G.remove_edge(u,v,k)
GLAZ={}
for u,v,d in G.edges(data=True):
    if "_geom" in d and d["type"] in ("window","glazed_door"):
        for r in (u,v):
            if r not in ("EXT","LOBBY"): GLAZ.setdefault(r,[]).append((d["_geom"],d["type"],(v if r==u else u),d["width_m"]))
for *_,d in G.edges(data=True): d.pop("_geom",None)
# drop doorless 'opening' where a door already joins the same pair
for u,v,k,d in list(G.edges(keys=True,data=True)):
    if d["type"]=="opening" and any(dd["type"]=="door" for dd in G.get_edge_data(u,v).values()): G.remove_edge(u,v,k)
# RERA polygon
from shapely.ops import polygonize
rl=unary_union([l for x in dr if x.get("layer")=="RERA AREA" for l in as_lines(x)])
rp=max(polygonize(rl),key=lambda g:g.area)
RERA_M2=rp.area*m*m
if __name__=="__main__":
    for n,dat in G.nodes(data=True): print(n,dat)
    for a,b,dat in G.edges(data=True):
        if dat["type"]!="wall": print(G.nodes[a]["name"],"<->",G.nodes[b]["name"],dat)
    print("wall edges",sum(1 for *_,d in G.edges(data=True) if d["type"]=="wall"))
