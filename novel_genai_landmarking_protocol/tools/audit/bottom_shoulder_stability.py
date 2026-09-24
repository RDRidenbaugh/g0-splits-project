"""Stability test behind the B12/B13 (shoulder) definition, protocol v1.2/v1.3 section 3.3.

40 random Bottom images (8 per group) x 8 outline perturbations; for each of 4
candidate definitions records the along-outline slide (in shaft widths) and the
axial position relative to the median basal notch. Results of the run cited in
the protocol: bottom_shoulder_stability_results.json (written before the v1.3
renumbering, so it refers to the notch as B12 and the shoulders as B13/B14).

usage: python bottom_shoulder_stability.py out.json
"""
import sys, csv, json, random, numpy as np, tifffile
sys.path.insert(0,'/home/labradorite/g0-splits-project/novel_genai_landmarking_protocol/tools')
from scipy import ndimage as ndi
from skimage.filters import threshold_otsu, gaussian
from skimage.measure import find_contours
from skimage.morphology import disk, opening, closing
from scheme import _basal_notch, _turning, _arc, _shoulder
from scipy.spatial import ConvexHull
L='/home/labradorite/g0-splits-project/lance_landmarking/'
rows=[r for r in csv.DictReader(open(L+'manifest.csv')) if r['angle']=='Bottom' and not r['flags']]
random.seed(7)
by={}
for r in rows: by.setdefault(r['group'],[]).append(r)
pick=[]
for g,rs in by.items(): pick+=random.sample(rs,min(8,len(rs)))
import os
if os.environ.get('ONLY'):
    only=set(open(os.environ['ONLY']).read().split()); pick=[r for r in pick if r['key'] in only]

def contour(img, old, sig, tscale, orad):
    a=gaussian(img.astype(float),sig,channel_axis=-1); rb=a[...,0]-a[...,2]; lum=a.mean(2)
    bgl=np.median(np.r_[lum[:30].ravel(),lum[-30:].ravel()])
    scl=(rb>threshold_otsu(rb)*tscale)|(lum<0.6*bgl)
    b=np.concatenate([a[:30].reshape(-1,3),a[-30:].reshape(-1,3)]); d=np.linalg.norm(a-np.median(b,0),axis=2)
    bgm=d>max(threshold_otsu(d)*tscale,25)
    base=(old[4]+old[16])/2; ax=(old[0]+old[12])/2-base; ax/=np.linalg.norm(ax)
    yy,xx=np.mgrid[:img.shape[0],:img.shape[1]]
    m=np.where((xx-base[0])*ax[0]+(yy-base[1])*ax[1]>0,bgm,opening(scl,disk(orad)))
    m=ndi.binary_fill_holes(closing(opening(m,disk(2)),disk(3)))
    lab,_=ndi.label(m); ids=[lab[int(y),int(x)] for x,y in old if lab[int(y),int(x)]>0]
    m=lab==np.bincount(ids).argmax()
    c=max(find_contours(gaussian(m.astype(float),0.75),0.5),key=len)[:,::-1]
    s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(c,axis=0),axis=1))]; t=np.arange(0,s[-1],1.0)
    return np.c_[np.interp(t,s,c[:,0]),np.interp(t,s,c[:,1])]

def cands(C, old, wscale=1.0):
    near=lambda p:int(np.argmin(np.linalg.norm(C-p,axis=1)))
    P={'B01':C[near(old[0])],'B02':C[near(old[12])],'B06':C[near(old[4])],'B10':C[near(old[16])]}
    P['B11']=_basal_notch(P,C,near)
    tip=(P['B01']+P['B02'])/2; ax=tip-P['B11']; ax/=np.linalg.norm(ax); nr=np.array([-ax[1],ax[0]])
    sw=np.linalg.norm(P['B06']-P['B10'])
    w=max(3,int(wscale*sw/3/1.0)); turn=_turning(C,w)
    out={}
    for side,su in (('L','B06'),('S','B10')):
        arc=_arc(C,near(P[su]),near(P['B11']),near(P['B01']))
        sg=np.sign((P[su]-P['B11'])@nr); lat=sg*((C[arc]-P['B11'])@nr)
        k=int(np.argmax(lat)); m=max(1,w//2)
        A=arc[m:k+1][np.argmin(turn[arc[m:k+1]])] if k+1>m else arc[k]
        tan=np.roll(C,-w,0)-np.roll(C,w,0)
        ang=np.degrees(np.arccos(np.clip(np.abs(tan[arc]@ax)/np.linalg.norm(tan[arc],axis=1),0,1)))
        hit=np.flatnonzero(ang[m:k+1]>=45); Cc=arc[m+hit[0]] if len(hit) else arc[k]
        # D: the production definition (tools/scheme.py::_shoulder)
        try:
            st={}; Dp=_shoulder(su,st)(P,C,near); D=near(Dp); out.setdefault('fb',{})[side]=st.get('fallback',0)
        except ValueError:
            D=arc[k]
        out[side]=dict(A=C[A],B=C[arc[k]],C=C[Cc],D=C[D])
        out[side]['fb']=out['fb'][side]
        # axial position relative to B12 (0) .. shoulder, as fraction of B12->tip length
        out[side]['axpos']={n:float((out[side][n]-P['B11'])@ax/np.linalg.norm(tip-P['B11'])) for n in 'ABCD'}
    return out,P,sw

# half resolution: blur sigma and morphology radii are halved to match
settings=[(1,1.0,7,1.0),(0.5,1.0,7,1.0),(1.75,1.0,7,1.0),(1,0.85,7,1.0),(1,0.93,7,1.0),(1,1.0,5,1.0),(1,1.0,7,0.7),(1,1.0,7,1.4)]
res=[]
for r in pick:
    try:
        img=tifffile.imread(L+r['raw_image'])[::2,::2,:3]; old=np.array(json.loads(r['landmarks_px_json']))/2
        ref,P,sw=None,None,None; runs=[]
        nfail=0
        for sig,ts,orad,ws in settings:
            try:
                C=contour(img,old,sig,ts,orad); o,Pp,swp=cands(C,old,ws)
            except Exception:
                nfail+=1; continue
            if ref is None: ref,P,sw=C,Pp,swp; s_ref=np.r_[0,np.cumsum(np.linalg.norm(np.diff(C,axis=0),axis=1))]
            # a perturbation whose notch jumps away from the reference is a segmentation failure
            if np.linalg.norm(Pp['B11']-P['B11'])>0.5*sw: nfail+=1; continue
            runs.append(o)
        if len(runs)<5: raise RuntimeError(f'only {len(runs)} usable perturbations')
        rec={'key':r['key'],'group':r['group'],'sw':sw,'nfail':nfail}
        for side in 'LS':
            for n in 'ABCD':
                pos=[s_ref[int(np.argmin(np.linalg.norm(ref-o[side][n],axis=1)))] for o in runs]
                rec[f'{side}{n}_sd']=float(np.std(pos))/sw
                rec[f'{side}{n}_ax']=runs[0][side]['axpos'][n]
                rec[f'{side}{n}_xy']=runs[0][side][n].tolist()
            rec[f'{side}_fallback']=int(runs[0][side]['fb'])
        rec['B11']=P['B11'].tolist(); res.append(rec); print(len(res),'/',len(pick),r['key'],'fails',nfail, {k:round(v,2) for k,v in rec.items() if k.endswith('_sd')}, flush=True)
    except Exception as e: print('FAIL',r['key'],e)
json.dump(res,open(sys.argv[1],'w'))
