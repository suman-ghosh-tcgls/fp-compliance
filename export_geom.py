exec(open("rules.py").read().replace('if __name__=="__main__":','if False:'))
import json
RM=fitz.open(PDF)[0].rotation_matrix
def disp(x,y): q=fitz.Point(x,y)*RM; return q.x,q.y
# metric frame: display orientation, metres, origin = bottom-left of unit floor extent, y up
U=unary_union([blue,tan,walls]); pts=[disp(*c) for g in (U.geoms if hasattr(U,"geoms") else [U]) for c in g.exterior.coords]
ox=min(p[0] for p in pts); oy=max(p[1] for p in pts)
def M(x,y):
    dx,dy=disp(x,y); return [round((dx-ox)*M_PER_PT,3),round((oy-dy)*M_PER_PT,3)]
out=json.load(open(os.path.join(OUTPUTS,"floorplan_graph.json")))
out["coordinate_system"]=dict(units="m",orientation="as displayed in the PDF viewer (page rotation applied)",
    origin="bottom-left corner of the unit's floor+wall extent",y_axis="up",scale_m_per_pt=M_PER_PT)
for n in out["nodes"]:
    k=n["id"]
    if k in("EXT","LOBBY"):
        if k=="LOBBY":
            d8=[dd for i,dd in enumerate(doors) if any(e.get("id")==f"D{i}" and "LOBBY" in (e["source"],e["target"]) for e in out["edges"])]
            n["anchor"]=M(*d8[0]["thr"].interpolate(.5,normalized=True).coords[0]) if d8 else None
        continue
    pg=comps[int(k)]["poly"].simplify(0.4)
    n["polygon"]=[M(*c) for c in pg.exterior.coords]
    n["anchor"]=M(*pg.representative_point().coords[0])
    n["centroid"]=M(*pg.centroid.coords[0])
for e in out["edges"]:
    i=e.get("id","")
    if e["type"]=="door" and i.startswith("D"):
        dd=doors[int(i[1:])]
        e["hinge"]=M(*dd["hinge"]); e["threshold"]=[M(*c) for c in dd["thr"].coords]; e["swing_end"]=M(*dd["open"])
    elif e["type"]=="opening" and i.startswith("O"):
        e["segment"]=[M(*c) for c in ops[int(i[1:])]["seg"].coords]
json.dump(out,open(os.path.join(OUTPUTS,"floorplan_graph.json"),"w"),indent=1,default=jsonable)
print(json.dumps([n for n in out["nodes"] if n["id"]=="8"][0])[:600])
print([e for e in out["edges"] if e.get("id")=="D8"])
