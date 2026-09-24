import numpy as np, glob
exec(open('/home/labradorite/g0-splits-project/novel_genai_landmarking_protocol/tools/audit/old_protocol_noise.py').read().split('for v,n in N.items():')[0])
tests={'Right':[(2,1,3),(1,30,2),(3,2,4),(6,5,7),(8,7,9),(13,12,28),(29,1,14)],
       'Left':[(2,1,3),(1,26,2),(3,2,4),(6,5,7),(8,7,9),(10,9,11),(13,12,32)],
       'Bottom':[(9,'axis',None),(6,7,12),(1,2,None),(13,14,None),(3,2,4),(15,14,16)]}
for v,n in N.items():
    A=np.array([np.loadtxt(f) for f in glob.glob(f'{base}/Landmarked_*/txt/{v}/*.txt') if len(np.loadtxt(f))==n]); A[:,:,1]*=-1
    X,m=gpa(A.copy()); res=X-m
    for lm,a,b in tests[v]:
        i=lm-1
        if a=='axis': t=(m[0]+m[12])/2-m[8]
        elif b is None: t=m[i]-m[a-1]
        else: t=m[b-1]-m[a-1]
        t/=np.linalg.norm(t); nrm=np.array([-t[1],t[0]])
        vt=(res[:,i]@t).var(); vn=(res[:,i]@nrm).var()
        print(f'{v:6s} LM{lm:2d} ref({a},{b}): tangential share of variance {vt/(vt+vn):.2f}   SD_t {np.sqrt(vt)*1000:.1f} SD_n {np.sqrt(vn)*1000:.1f}')
