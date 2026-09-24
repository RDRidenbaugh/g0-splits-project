import numpy as np, glob, json, os, collections
base='/home/labradorite/g0-splits-project/novel_genai_landmarking_protocol/Landmarked_Images'
runs='/home/labradorite/g0-splits-project/lance_landmarking/model/runs/21ix26_runs'
N={'Bottom':17,'Left':32,'Right':36}
def gpa(X):
    X=X-X.mean(1,keepdims=True); X=X/np.linalg.norm(X,axis=(1,2),keepdims=True)
    m=X[0].copy()
    for _ in range(20):
        for i in range(len(X)):
            u,s,vt=np.linalg.svd(X[i].T@m); X[i]=X[i]@(u@vt)
        m2=X.mean(0); m2/=np.linalg.norm(m2)
        if np.abs(m2-m).max()<1e-10: break
        m=m2
    return X,m
for v,n in N.items():
    files=[f for f in glob.glob(f'{base}/Landmarked_*/txt/{v}/*.txt')]
    cnt=collections.Counter(); groups=[]; A=[]
    for f in files:
        a=np.loadtxt(f); cnt[len(a)]+=1
        if len(a)==n: A.append(a); groups.append(f.split('/')[-4])
    A=np.array(A); A[:,:,1]*=-1
    X,m=gpa(A.copy())
    csize=np.sqrt(((A-A.mean(1,keepdims=True))**2).sum((1,2)))
    res=X-m; sd=np.sqrt((res**2).sum(2).mean(0))
    ev=json.load(open(glob.glob(f'{runs}/{v}_*/eval_test.json')[0]))
    pl=ev['per_landmark_mean_px_error']
    pl=[pl[str(i)] if isinstance(pl,dict) else pl[i] for i in range(n)] if not isinstance(pl,dict) else [pl.get(str(i+1),pl.get(str(i))) for i in range(n)]
    print(f'\n== {v}: files {len(files)} point-count dist {dict(cnt)}; n used {len(A)}; centroid size mm mean {csize.mean():.3f} CV {csize.std()/csize.mean():.3f}')
    order=np.argsort(-sd)
    print('LM  procrustesSD(x1000)  CNNerr_px')
    for i in range(n): print(f'{i+1:3d} {sd[i]*1000:8.2f} {pl[i]:8.1f}')
    # PCA
    Z=X.reshape(len(X),-1); Z=Z-Z.mean(0); u,s,vt=np.linalg.svd(Z,full_matrices=False); var=s**2/ (s**2).sum()
    print('PC var %:', np.round(var[:6]*100,1))
    pc1=vt[0].reshape(n,2); print('PC1 top loading LMs:', (np.argsort(-np.linalg.norm(pc1,axis=1))[:6]+1).tolist())
    g=np.array(groups); sc=u[:,:4]*s[:4]
    for k in range(4):
        y=sc[:,k]; ssb=sum(((y[g==G].mean()-y.mean())**2)*(g==G).sum() for G in set(g)); print(f'  PC{k+1} group R2={ssb/((y-y.mean())**2).sum():.3f}', end='')
    print()
