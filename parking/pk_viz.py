exec(open("pk_check.py").read().replace('if __name__=="__main__":','if False:'))
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
pix=p.get_pixmap(dpi=144) if p.rotation else None
d2=fitz.open(PARKING_PDF); p2=d2[0]
R=fitz.Rect(205,95,565,475); pix=p2.get_pixmap(dpi=144,clip=R)
img=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width,pix.n)[:,:,:3]
fig,ax=plt.subplots(figsize=(13,13)); ax.imshow(img,extent=(R.x0,R.x1,R.y1,R.y0),alpha=.45)
def fill(g,**k):
    for q in (g.geoms if hasattr(g,"geoms") else [g]):
        if q.geom_type=="Polygon": x,y=q.exterior.xy; ax.fill(x,y,**k)
fill(clear,color="gold",alpha=.25,lw=0)
for b in bays:
    c="tab:green" if b["front"] else ("tab:blue" if b.get("via") else "tab:red")
    x,y=b["poly"].exterior.xy; ax.fill(x,y,color=c,alpha=.45,lw=0)
ys,xs=np.where(core); ax.scatter(xs/S+X0,ys/S+Y0,s=.2,c=dt[core],cmap="RdYlGn",vmin=3,vmax=6.5)
for nk in necks: ax.annotate("%.2f m"%nk["w"],nk["pt"],xytext=(nk["pt"][0]+10,nk["pt"][1]-12),color="crimson",fontsize=11,arrowprops=dict(arrowstyle="->",color="crimson"))
ax.set_xlim(R.x0,R.x1); ax.set_ylim(R.y1,R.y0); ax.axis("off"); fig.savefig(os.path.join(OUTPUTS,"parking_P1_check.png"),dpi=90,bbox_inches="tight")
