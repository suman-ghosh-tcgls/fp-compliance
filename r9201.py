src=open("rules.py").read().replace('if __name__=="__main__":','if False:')
# keep glazing geometry per room before graph.py discards it
g=open("graph.py").read().replace('for *_,d in G.edges(data=True): d.pop("_geom",None)',
 'GLAZ={}\nfor u,v,d in G.edges(data=True):\n    if "_geom" in d and d["type"] in ("window","glazed_door"):\n        for r in (u,v):\n            if r not in ("EXT","LOBBY"): GLAZ.setdefault(r,[]).append((d["_geom"],d["type"],(v if r==u else u),d["width_m"]))\nfor *_,d in G.edges(data=True): d.pop("_geom",None)')
open("graph_g.py","w").write(g)
exec(src.replace("from graph import *","exec(open('graph_g.py').read().replace('if __name__==\"__main__\":','if False:'))"))
import numpy as np, json
# thresholds, room kinds and light-admitting targets come from the configured rule record
RULE=next(r for r in json.load(open(os.path.join("rules","udcpr_rules_v1.json")))["rules"] if r["id"]=="UDCPR-9.20.1")
CK={c["id"]:c for c in RULE["checks"]}
RATIO=CK["opening_ratio"]["value"]; DEPTH=CK["depth"]["value"]
TARGETS=set(CK["depth"]["quantity"]["args"]["to"])   # e.g. exterior, open_deck
def target_of(n):   # graph node -> rule target class; deck vs utility by name until the kind taxonomy exists
    if n=="EXT": return "exterior"
    if G.nodes[n]["kind"]=="service_open": return "open_deck" if "deck" in G.nodes[n]["name"].lower() else "service_open"
    return G.nodes[n]["kind"]
checks=[]
def add(check,k,status,detail,**vals):
    checks.append(dict(rule=RULE["id"],clause=RULE["clause"],check=check,space_id=str(k),space=G.nodes[k]["name"],
                       status=status,detail=detail,**vals))
def desc(x): return f'{x[1].replace("_"," ")} to {G.nodes[x[2]]["name"] if x[2]!="EXT" else "exterior"} {x[3]:.2f} m'
for k in keep:
    n=G.nodes[k]
    if n["kind"] not in RULE["applies_to"]["kind"]: continue
    allgl=GLAZ.get(k,[]); gl=[x for x in allgl if target_of(x[2]) in TARGETS]
    other=[x for x in allgl if x not in gl]
    A=n["area_m2"]; need=RATIO*A; width=sum(x[3] for x in gl)
    if not gl:
        why=(f'no glazing to {"/".join(sorted(TARGETS))}; only '+", ".join(desc(x) for x in other)+
             ' - decide whether that space counts as a light source') if other else f'no glazing to {"/".join(sorted(TARGETS))}'
        add("opening_ratio",k,"REVIEW",why,area_m2=A,required_opening_m2=round(need,2))
        add("depth",k,"REVIEW",why,limit_m=DEPTH)
        continue
    h_req=need/width
    add("opening_ratio",k,"CANNOT DETERMINE",
        f'needs {need:.2f} m2 of openings ({RATIO:g} x {A:.2f} m2); glazed width {width:.2f} m, so openings must be at least '
        f'{h_req:.2f} m high on average - opening head/sill heights are not in the drawing; via '+", ".join(desc(x) for x in gl),
        area_m2=A,required_opening_m2=round(need,2),glazed_width_m=round(width,2),min_opening_height_m=round(h_req,2))
    # depth: farthest floor point (2 pt grid) from any light-admitting opening
    U=unary_union([x[0] for x in gl]); pg=comps[k]["poly"]
    xs=np.arange(pg.bounds[0],pg.bounds[2],2.0); ys=np.arange(pg.bounds[1],pg.bounds[3],2.0)
    dist=[U.distance(Point(x,y))*M_PER_PT for x in xs for y in ys if pg.contains(Point(x,y))]
    dmax=max(dist); far=sum(d>DEPTH for d in dist)/len(dist)
    add("depth",k,"PASS" if dmax<=DEPTH else "FAIL",
        f'farthest floor point {dmax:.1f} m from the nearest opening (limit {DEPTH:g} m)'+
        (f'; {100*far:.0f}% of the floor is beyond the limit' if dmax>DEPTH else ""),
        max_distance_m=round(dmax,2),limit_m=DEPTH,share_beyond_limit=round(far,3))
out=dict(source=os.path.basename(PDF),rules_file="rules/udcpr_rules_v1.json",scale_m_per_pt=M_PER_PT,
         note="checks = configured rule records that select elements present in this plan (only UDCPR-9.20.1 for a unit plan)",
         checks=checks)
json.dump(out,open(os.path.join(OUTPUTS,"floorplan_checks.json"),"w"),indent=1,default=jsonable)
for c in checks: print(f'{c["status"]:17} {c["rule"]} {c["check"]:14} {c["space"]:24} {c["detail"]}')
