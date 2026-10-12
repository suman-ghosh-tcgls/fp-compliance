exec(open("rules.py").read().replace('if __name__=="__main__":','if False:'))
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
d_=fitz.open(PDF); p_=d_[0]; RM=p_.rotation_matrix   # page as the viewer shows it
def T(x,y):
    q=fitz.Point(x,y)*RM; return q.x,q.y
xs_,ys_=zip(*[T(x,y) for x in (X0,X1) for y in (Y0,Y1)])
DX0,DX1,DY0,DY1=min(xs_),max(xs_),min(ys_),max(ys_)
pix=p_.get_pixmap(dpi=144,clip=fitz.Rect(DX0,DY0,DX1,DY1))
img=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width,pix.n)[:,:,:3]
fig,ax=plt.subplots(figsize=(14,11))
ax.imshow(img,extent=(DX0,DX1,DY1,DY0),alpha=.35)
cols=plt.cm.tab20(np.linspace(0,1,len(keep)))
for c_,k in zip(cols,keep):
    pg=comps[k]["poly"]; x,y=zip(*[T(*c) for c in pg.exterior.coords]); ax.fill(x,y,color=c_,alpha=.35,lw=0)
pos={k:np.array(comps[k]["poly"].representative_point().coords[0]) for k in keep}
pos[7]=np.array(comps[7]["poly"].centroid.coords[0])
pos["LOBBY"]=np.array([178,352]); pos["EXT"]=np.array([470,600])
pos={k:np.array(T(*v)) for k,v in pos.items()}
style={"door":("tab:red","-",2.4),"opening":("tab:orange","--",2.4),"glazed_door":("tab:blue","-",2.4),"window":("tab:cyan",":",1.4),"wall":("0.45","-",0.8)}
# flag spaces from the configured checks (r9201.py), not from the R1-R7 prototype checks
CHK=os.path.join(OUTPUTS,"floorplan_checks.json")
flag_ids={c["space_id"] for c in json.load(open(CHK))["checks"] if c["status"] in ("FAIL","REVIEW")} if os.path.exists(CHK) else set()
for a,b,d in G.edges(data=True):
    if d["type"]=="window":
        # draw window edges as short ticks toward nearest facade instead of to a global EXT point
        pa=pos[a if b=="EXT" else b]; ax.plot(*pa,marker=(3,0,0),ms=0); continue
    c,ls,lw=style[d["type"]]
    pa,pb=pos[a],pos[b]; off=0
    if d["type"]=="wall": off=1.5
    ax.plot([pa[0]+off,pb[0]+off],[pa[1]+off,pb[1]+off],color=c,ls=ls,lw=lw,zorder=3)
    if d["type"] in("door","opening","glazed_door"):
        mid=(pa+pb)/2; ax.text(mid[0],mid[1],f'{d["width_m"]:.2f}',fontsize=6.5,color=c,ha="center",va="center",
                              bbox=dict(boxstyle="round,pad=.15",fc="white",ec="none",alpha=.8),zorder=5)
for k in keep+["LOBBY"]:
    n=G.nodes[k]; nw=len(G.get_edge_data(k,"EXT") or {})
    lbl=n["name"].replace(" / ","/\n") + (f'\n{n["area_m2"]:.1f} m²' if k!="LOBBY" else "")
    if k!="LOBBY" and nw: lbl+=f"  ☼{nw}"
    fl=str(k) in flag_ids
    ax.scatter(*pos[k],s=70,c="white",edgecolors="crimson" if fl else "k",linewidths=2 if fl else 1,zorder=6)
    ax.text(pos[k][0]+3,pos[k][1]-3,lbl,fontsize=7.5,zorder=7,bbox=dict(boxstyle="round,pad=.2",fc="white",ec="none",alpha=.85))
leg=[Line2D([0],[0],color=style[t][0],ls=style[t][1],lw=2,label=l) for t,l in
     [("door","door (leaf width m)"),("opening","doorless opening"),("glazed_door","sliding/glazed door"),("wall","shares a wall")]]
leg.append(Line2D([0],[0],marker="o",color="w",markeredgecolor="crimson",markeredgewidth=2,ms=8,label="space with a FAIL/REVIEW rule check"))
ax.legend(handles=leg,loc="lower left",fontsize=8,framealpha=.9)
ax.text(DX0+5,DY0+8,"☼n = number of exterior windows",fontsize=8)
ax.set_xlim(DX0,DX1); ax.set_ylim(DY1,DY0); ax.set_aspect("equal"); ax.axis("off")
ax.set_title("Tower Q 4.5BHK — extracted space graph",fontsize=12)
fig.savefig(os.path.join(OUTPUTS,"floorplan_graph.png"),dpi=130,bbox_inches="tight")
