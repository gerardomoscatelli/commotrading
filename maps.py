"""Render SA weather maps to PNG (matplotlib + cartopy; Natural Earth shapes are downloaded by cartopy on first run)."""
import os, numpy as np, matplotlib; matplotlib.use("Agg")
import matplotlib.patheffects as pe, matplotlib.pyplot as plt, cartopy.crs as ccrs, cartopy.feature as cf
from scipy.interpolate import RegularGridInterpolator
OUT=os.path.join(os.path.dirname(__file__),"data","maps"); os.makedirs(OUT,exist_ok=True)
EXT=[-65.9,-44.1,-37.9,-8.1]
LABELS=[("BRAZIL",-50,-12,10,True),("ARGENTINA",-64.5,-26.5,10,True),("PARAGUAY",-59.5,-22.5,8,True),("BOLIVIA",-65.5,-16,8,True),("URUGUAY",-56.8,-33.2,7,True),
 ("Mato Grosso",-56,-13,8,False),("Goiás",-50.2,-16,8,False),("Paraná",-52.5,-24.6,8,False),("RS",-53.5,-29.5,8,False),
 ("Buenos Aires",-61,-36.5,8,False),("Córdoba",-64.2,-31.8,8,False),("Santa Fe",-61,-30.2,8,False),("MS",-54.8,-20.5,7,False)]
def _up(la,lo,z,f=4):
    la=np.array(la);lo=np.array(lo);Z=np.array(z,dtype=float).reshape(len(la),len(lo))
    it=RegularGridInterpolator((la,lo),Z,bounds_error=False,fill_value=None)
    la2=np.linspace(la[0],la[-1],(len(la)-1)*f+1);lo2=np.linspace(lo[0],lo[-1],(len(lo)-1)*f+1)
    G=np.stack(np.meshgrid(la2,lo2,indexing="ij"),-1);return lo2,la2,it(G)
def render(name,la,lo,z,title,unit,cmap,levels):
    X,Y,Z=_up(la,lo,z)
    fig=plt.figure(figsize=(4.6,5.6),dpi=110,facecolor="#f4f1ea")
    ax=fig.add_axes([0.02,0.15,0.96,0.78],projection=ccrs.PlateCarree());ax.set_extent(EXT,ccrs.PlateCarree())
    cs=ax.contourf(X,Y,Z,levels=levels,cmap=cmap,extend="both",transform=ccrs.PlateCarree(),zorder=1)
    ax.add_feature(cf.OCEAN.with_scale("50m"),facecolor="#bcdcf2",zorder=2)
    ax.add_feature(cf.LAKES.with_scale("50m"),facecolor="#bcdcf2",edgecolor="#555",lw=.4,zorder=2)
    ax.add_feature(cf.STATES.with_scale("50m"),edgecolor="#1a1a1a",lw=1.1,facecolor="none",zorder=3,alpha=.7)
    ax.add_feature(cf.STATES.with_scale("50m"),edgecolor="#e6ebf0",lw=.5,facecolor="none",zorder=3)
    for ft in (cf.BORDERS,cf.COASTLINE):
        ax.add_feature(ft.with_scale("50m"),edgecolor="#000000",lw=2.6,zorder=4)
        ax.add_feature(ft.with_scale("50m"),edgecolor="#ffffff",lw=1.3,zorder=4)
    for t,x,y,s,c in LABELS:
        ax.text(x,y,t,fontsize=s+(1 if c else 0),color="#1f4e79" if c else "#222",weight="bold",ha="center",zorder=5,transform=ccrs.PlateCarree(),
          path_effects=[pe.withStroke(linewidth=2.2,foreground="#f4f1ea")] if c else None,
          bbox=None if c else dict(boxstyle="round,pad=.15",fc="#ffffffd0",ec="none"))
    ax.set_title(title,color="#222",fontsize=11,weight="bold")
    ax.spines["geo"].set_edgecolor("#999")
    cax=fig.add_axes([0.08,0.085,0.84,0.025]);cb=fig.colorbar(cs,cax=cax,orientation="horizontal")
    cb.set_label(unit,color="#222",fontsize=9);cb.ax.tick_params(colors="#222",labelsize=8);cb.outline.set_edgecolor("#888")
    fig.savefig(os.path.join(OUT,name+".png"),facecolor=fig.get_facecolor());plt.close(fig)
def render_all(w,c=None):
    render("precip",w["lat"],w["lon"],w["precip7"],"7-day precipitation","mm (7-day total)","YlGnBu",[0,2,5,10,15,20,30,40,50,75,100,150])
    T=[v if v is not None else np.nan for v in w["tmax7"]]
    render("tmax",w["lat"],w["lon"],T,"Mean daily max temperature","°C (7-day mean)","RdYlBu_r",list(range(14,42,2)))
    if c and c.get("clim7"):
        from sources import _grid
        cla,clo=_grid(2.0);X,Y,C=_up(cla,clo,c["clim7"],1)
        it=RegularGridInterpolator((np.array(cla),np.array(clo)),C,bounds_error=False,fill_value=None)
        G=np.stack(np.meshgrid(w["lat"],w["lon"],indexing="ij"),-1);an=np.array(w["precip7"]).reshape(G.shape[:2])-it(G)
        render("anom",w["lat"],w["lon"],an.ravel(),"Precip anomaly vs "+c.get("years",""),"mm vs normal (7 days)","RdBu",[-80,-50,-30,-20,-10,-5,5,10,20,30,50,80])
        return True
    return False
