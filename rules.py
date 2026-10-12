from graph import *
import json
# ---- rule thresholds: ILLUSTRATIVE (NBC-2016-style); replace with the governing DCR/UDCPR table ----
MIN={"bedroom":(9.5,2.4),"living":(9.5,2.4),"kitchen":(5.0,1.8),"toilet":(1.8,1.2)}
DOOR_MIN={"main":1.0,"habitable":0.9,"toilet":0.75}
TOL=0.05
res=[]
def R(rule,node,ok,detail): res.append(dict(rule=rule,space=node,status="PASS" if ok else "FLAG",detail=detail))
N=G.nodes
rooms=[k for k in keep]
# R1 reachability from the common lobby through doors/openings/glazed doors
H=nx.Graph([(a,b) for a,b,d in G.edges(data=True) if d["type"] in("door","opening","glazed_door")])
for k in rooms:
    ok=H.has_node(k) and nx.has_path(H,"LOBBY",k)
    path=nx.shortest_path(H,"LOBBY",k) if ok else []
    R("R1 reachable from entrance",N[k]["name"],ok,"via "+" > ".join(N[p]["name"] for p in path) if ok else "no access path")
# R2 natural light: habitable rooms need a window to exterior, or glazing onto an open deck
for k in rooms:
    if N[k]["kind"] not in("bedroom","living","kitchen"): continue
    direct=[d for nb in G[k] for d in G[k][nb].values() if nb=="EXT" and d["type"]=="window"]
    via_deck=[d for nb in G[k] for d in G[k][nb].values() if d["type"]=="glazed_door" and N[nb]["kind"]=="service_open"]
    w=sum(d["width_m"] for d in direct+via_deck)
    R("R2 window to exterior",N[k]["name"],bool(direct or via_deck),
      f"{len(direct)} direct window(s), {len(via_deck)} glazed door(s) onto deck/utility, total glazed width {w:.2f} m" )
# R3 toilet must not open directly into kitchen; flag dining adjacency as advisory
for a,b,d in G.edges(data=True):
    if d["type"]!="door": continue
    for t,o in ((a,b),(b,a)):
        if N[t].get("kind")=="toilet":
            kit = N[o].get("kind")=="kitchen"
            # inside open-plan zones, find which labelled function the door lands in
            sub=""
            if N[o].get("kind")=="living":
                dd=doors[int(d["id"][1:])]; mid=np.array(dd["thr"].interpolate(.5,normalized=True).coords[0])
                Ls=comps[o]["labels"]; near=min(Ls,key=lambda L:np.hypot(L["pt"][0]-mid[0],L["pt"][1]-mid[1]))
                sub=near["name"]
            R("R3 toilet door not into kitchen",N[t]["name"],not kit and sub!="Kitchen",
              f"door {d['id']} opens into {N[o]['name']}"+(f" (nearest function: {sub})" if sub else ""))
# R4 minimum area and width
for k in rooms:
    kd=N[k]["kind"]
    if kd not in MIN: continue
    a,w=MIN[kd]; A=N[k]["area_m2"]; Wd=float(N[k]["min_width_m"])
    R("R4 min area / width",N[k]["name"],A>=a and Wd>=w,f"area {A:.2f} m2 (min {a}), clear width {Wd:.2f} m (min {w})")
# R5 door widths (leaf width from swing radius; clear opening is smaller)
for a,b,d in G.edges(data=True):
    if d["type"]!="door": continue
    ks={N[a].get("kind"),N[b].get("kind")}
    cls="main" if "exterior" in ks and "living" in ks else "toilet" if "toilet" in ks else "habitable"
    lim=DOOR_MIN[cls]
    R("R5 door width",f"{d['id']} {N[a]['name']} | {N[b]['name']}",d["width_m"]>=lim,f"leaf {d['width_m']:.2f} m vs {cls} min {lim}")
# R6 drawn geometry vs labelled dimensions
for k in rooms:
    for L in comps[k]["labels"]:
        if len(comps[k]["labels"])>1: continue
        lab_=sorted(L["dim"]); meas=sorted(N[k]["obb_m"])
        err=max(abs(x-y)/y for x,y in zip(meas,lab_))
        R("R6 label matches geometry",N[k]["name"],err<=TOL,f"label {lab_[0]:.2f} x {lab_[1]:.2f}, measured {meas[0]:.2f} x {meas[1]:.2f} ({err*100:.0f}% max dev)")
# R7 RERA area statement vs drawn RERA boundary
R("R7 RERA area consistent","Unit",abs(RERA_M2-194.66)/194.66<=0.02,f"stated 194.66 m2, RERA polyline {RERA_M2:.2f} m2, sum of free floor cells {sum(N[k]['area_m2'] for k in rooms):.2f} m2")
def jsonable(o):
    if isinstance(o,(np.floating,)): return float(o)
    if isinstance(o,(np.integer,)): return int(o)
    if isinstance(o,tuple): return list(o)
    return str(o)
if __name__=="__main__":
    for r in res: print(f"{r['status']:4} {r['rule']:28} {r['space']:40} {r['detail']}")
    out=dict(source=os.path.basename(PDF),scale_m_per_pt=M_PER_PT,
             nodes=[dict(id=str(n),**{k:v for k,v in d.items()}) for n,d in G.nodes(data=True)],
             edges=[dict(source=str(a),target=str(b),**d) for a,b,d in G.edges(data=True)])   # R1-R7 are not configured rules: printed only
    json.dump(out,open(os.path.join(OUTPUTS,"floorplan_graph.json"),"w"),indent=1,default=jsonable)
