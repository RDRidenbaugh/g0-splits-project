"""Evidence audit of the old 32-point saw protocol (ovipositor_morphometrics_protocol_v6).

1. Inter-observer error: 14 specimens digitized on the same image by BH and GK.
2. Error direction: share of each point's error along the local outline (slidable) vs across it.
3. Population GPA: per-point Procrustes SD and PC1 loadings, all 404 configs and by species.
4. LM14 (9th annulus in lecontei, pre-apical notch in pinetum): how much it alone drives the species axis.
Writes analysis/output/old_protocol_audit.json.
"""
import collections, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from load_old import load, specimen_key, match_by_coords, CAL, ROOT

# polylines that give each point's local tangent (old numbering, 1-based)
CHAINS = [list(range(1, 16)), [16, 17, 18, 19, 20, 21, 22], [25, 23, 24], list(range(25, 33)) + [15]]


def tangents(X):
    T = np.zeros_like(X)
    for ch in CHAINS:
        idx = [i - 1 for i in ch]
        for j, i in enumerate(idx):
            a = X[idx[max(j - 1, 0)]]; b = X[idx[min(j + 1, len(idx) - 1)]]
            t = b - a; n = np.linalg.norm(t)
            if n > 0 and not T[i].any():
                T[i] = t / n
    return T


def procrustes(A, iters=10):
    A = A - A.mean(1, keepdims=True)
    cs = np.sqrt((A ** 2).sum((1, 2)))
    A = A / cs[:, None, None]
    M = A[0]
    for _ in range(iters):
        for k in range(len(A)):
            u, s, vt = np.linalg.svd(A[k].T @ M)
            A[k] = A[k] @ (u @ vt)
        M = A.mean(0); M /= np.sqrt((M ** 2).sum())
    return A, cs, M


def species_of(rec, meta, idmap_rev):
    pid = idmap_rev.get(rec['file'])
    if pid:
        return meta[pid]['Species'].upper(), pid
    s = os.path.basename(rec['file']).upper()
    if s.startswith(('NP', '087', '097', '196', '088', '085', '102', '174', '185', '076')):
        return 'PINETUM?', None
    return 'LECONTEI?', None


def main():
    recs, meta = load()
    idmap, _ = match_by_coords(recs, meta)
    rev = {recs[i]['file']: pid for pid, i in idmap.items()}
    out = {}

    # 1-2 inter-observer
    g = collections.defaultdict(list)
    for r in recs:
        g[specimen_key(r)].append(r)
    pairs = []
    for k, v in g.items():
        bh = [r for r in v if r['folder'] == 'BH']; gk = [r for r in v if r['folder'] == 'GK']
        if bh and gk and bh[0].get('side') == gk[0].get('side'):
            pairs.append((k, bh[0]['xy_mm'][:32] * CAL, gk[0]['xy_mm'][:32] * CAL))
    err = np.array([np.linalg.norm(a - b, axis=1) for _, a, b in pairs])
    along = np.zeros((len(pairs), 32)); across = np.zeros_like(along)
    for j, (_, a, b) in enumerate(pairs):
        T = tangents((a + b) / 2); d = a - b
        along[j] = (d * T).sum(1); across[j] = d[:, 0] * -T[:, 1] + d[:, 1] * T[:, 0]
    # exclude the one pair with an annulus-identity shift from the per-point summaries
    shift = [j for j in range(len(pairs)) if err[j].max() > 150]
    keep = [j for j in range(len(pairs)) if j not in shift]
    um = 1000 / CAL
    out['interobserver'] = dict(
        n_pairs=len(pairs), identity_shift_pairs=[pairs[j][0] for j in shift],
        median_um=[round(float(np.median(err[keep, i]) * um), 1) for i in range(32)],
        rms_um=[round(float(np.sqrt((err[keep, i] ** 2).mean()) * um), 1) for i in range(32)],
        share_along=[round(float((along[keep, i] ** 2).sum() / ((along[keep, i] ** 2).sum() + (across[keep, i] ** 2).sum())), 2) for i in range(32)],
        overall_median_um=round(float(np.median(err[keep]) * um), 1))

    # 3-4 population
    X = [r for r in recs if r['n'] >= 32]
    A = np.array([r['xy_mm'][:32] for r in X])
    sp = [species_of(r, meta, rev)[0] for r in X]
    P, cs, M = procrustes(A.copy())
    sd = np.sqrt(((P - M) ** 2).sum(2).mean(0))
    flat = (P - M).reshape(len(P), -1)
    u, s, vt = np.linalg.svd(flat, full_matrices=False)
    var = s ** 2 / (s ** 2).sum()
    load1 = np.linalg.norm(vt[0].reshape(32, 2), axis=1)
    lec = np.array([x.startswith('LEC') for x in sp]); pin = np.array([x.startswith('PIN') for x in sp])
    def r2(Pk):
        f = Pk.reshape(len(Pk), -1); tot = ((f - f.mean(0)) ** 2).sum()
        wit = ((f[lec] - f[lec].mean(0)) ** 2).sum() + ((f[pin] - f[pin].mean(0)) ** 2).sum()
        return 1 - wit / tot
    keep_idx = [i for i in range(32) if i != 13]
    P2, _, _ = procrustes(A[:, keep_idx].copy())
    # distance LM14 -> apex (15) relative to 13 -> 15, by species
    rel = np.linalg.norm(A[:, 13] - A[:, 14], axis=1) / np.linalg.norm(A[:, 12] - A[:, 14], axis=1)
    out['population'] = dict(
        n=len(X), n_lec=int(lec.sum()), n_pin=int(pin.sum()),
        procrustes_sd_x1000=[round(float(v * 1000), 1) for v in sd],
        pc_var=[round(float(v), 3) for v in var[:6]],
        pc1_loading_top=[int(i + 1) for i in np.argsort(-load1)[:6]],
        species_R2_all32=round(float(r2(P)), 3), species_R2_without_LM14=round(float(r2(P2)), 3),
        lm14_rel_position_median=dict(lec=round(float(np.median(rel[lec])), 2), pin=round(float(np.median(rel[pin])), 2)),
        csize_mm=dict(lec=round(float(np.median(cs[lec])), 3), pin=round(float(np.median(cs[pin])), 3)))
    os.makedirs(os.path.join(ROOT, 'analysis/output'), exist_ok=True)
    json.dump(out, open(os.path.join(ROOT, 'analysis/output/old_protocol_audit.json'), 'w'), indent=1)
    io = out['interobserver']
    print('pairs', io['n_pairs'], 'shift', io['identity_shift_pairs'], 'overall median um', io['overall_median_um'])
    for i in range(32):
        print(f"LM{i+1:2d} inter-obs median {io['median_um'][i]:5.1f} rms {io['rms_um'][i]:5.1f} um  along {io['share_along'][i]:.2f}  ProcSD {out['population']['procrustes_sd_x1000'][i]:5.1f}")
    print(json.dumps(out['population'], indent=0))


if __name__ == '__main__':
    main()
