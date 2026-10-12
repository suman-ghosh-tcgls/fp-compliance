exec(open("pk_check.py").read().replace('if __name__=="__main__":','if False:'))
import json
RM_=fitz.open(PARKING_PDF)[0].rotation_matrix
ox,oy=205,475
def M(x,y): return [round((x-ox)*S_M,2),round((oy-y)*S_M,2)]
out=dict(source=os.path.basename(PARKING_PDF)+" (P1 at +554.10)",
  scale=dict(m_per_pt=S_M,basis="RERA AREA dimension 16.2 pt labelled 2.76 m (lift lobby); cross-check: lift doors 0.89-0.90 m"),
  coordinate_system=dict(units="m",orientation="as displayed",origin="display point (205,475) pt",y_axis="up"),
  bays=[], aisle=dict(clear_area_m2=round(clear.area*S_M**2,1),typical_clear_width_m=round(float(np.median(cw)),2),
        min_clear_width_m=round(float(cw.min()),2),narrowings=[dict(width_m=round(n_["w"],2),length_m=round(n_["len_m"],1),at=M(*n_["pt"])) for n_ in necks]),
  checks=[], observations=[])
for i,b in enumerate(bays):
    c=tuple(round(v) for v in b["poly"].centroid.coords[0])
    acc="aisle" if b["front"] else ("via tandem partner" if b.get("via") else "no aisle frontage detected")
    out["bays"].append(dict(id=f"B{i}",type="tandem" if b["tandem"] else "standard",width_m=round(b["w"],2),length_m=round(b["l"],2),
        access=acc,gap_to_aisle_m=round(min(LineString([b["xs"][i],b["xs"][i+1]]).distance(drive) for i in range(4))*S_M,2),polygon=[M(*q) for q in b["poly"].exterior.coords]))
C=out["checks"]
def add(rule,item,status,detail): C.append(dict(rule=rule,item=item,status=status,detail=detail))
OBS=out["observations"]
def obs(topic,detail): OBS.append(dict(topic=topic,detail=detail,note="drawing observation, not one of the provided rules"))
ws=[b["w"] for b in bays]; ls=[b["l"] for b in bays]
add("UDCPR-8.1.1 car bay >= 2.5 x 5.0 m","64 bays","PASS (at limit)",f"all bays {min(ws):.2f}-{max(ws):.2f} x {min(ls):.2f}-{max(ls):.2f} m; scale uncertainty about ±0.2%")
obs("Legend vs drawn bay size","legend states 2.5 x 5.5 m 'big car' bays; drawn bays are 2.5 x 5.0 m. Counts match legend (64 total, 16 tandem)")
add("UDCPR-8.1.1 drive width >= 3.0 m","Drive aisle","PASS",f"typical clear width {np.median(cw):.2f} m (two-way); narrowest {cw.min():.2f} m at the NE taper")
nrev=sum(1 for b in out["bays"] if b["access"]=="no aisle frontage detected")
obs("Bays without detected aisle frontage",f"{nrev} of 64 bays have no edge facing the drive aisle or a tandem partner; see bays[].access and gap_to_aisle_m")
add("UDCPR-8.1.1 2W bay >= 1.0 x 2.0 m","2W spaces","CANNOT DETERMINE","2W parking drawn as labelled zones ('SPACE FOR TWO WHEELER PARKING') without individual bays")
add("UDCPR-9.12.2 ramp width >= 3.0 m","West exit ramp","PASS","hatched ramp strip 3.63 m between edges")
add("UDCPR-9.12.2 ramp slope <= 1:8","Ramps","PASS (annotation only)","annotated 1:10 (exit) and 1:12 (two south ramps); geometric slope not verifiable: south ramps run off this sheet and level tags need the section")
add("UDCPR-9.12.2 number of ramps","Ramps","CANNOT DETERMINE","needs all parking levels + plot area for the <=1000/<=2000 sq.m exceptions")
obs("Level annotations","P1 plan labels a ramp 'UP TO P1' and another 'UP TO P2' though P2 (+550.8) is below P1 (+554.1); road level tags +552.00 (exit), +547.5 (entry), +548.00 (east)")
SHOW_OBS=os.environ.get("INCLUDE_OBSERVATIONS")=="1"   # observations are hidden by default
if not SHOW_OBS: out.pop("observations",None)
json.dump(out,open(os.path.join(OUTPUTS,"parking_P1_checks.json"),"w"),indent=1)


for c in C: print(f'{c["status"]:22} {c["rule"]:38} {c["detail"]}')
if SHOW_OBS:
    print("--- observations (not rules)")
    for o in OBS: print(" -",o["topic"],":",o["detail"])
