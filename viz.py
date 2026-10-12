import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from shapely.geometry import MultiPolygon
def plotpoly(ax,g,**kw):
    for pg in (g.geoms if hasattr(g,"geoms") else [g]):
        if pg.is_empty or pg.geom_type!="Polygon": continue
        x,y=pg.exterior.xy; ax.fill(x,y,**kw)
