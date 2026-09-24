"""Contact sheet of automatic labels drawn on their raw images, for visual spot checks.

usage: python autolabel_sheet.py <View> <pass|fail> <n> <out.jpg> [seed]
"""
import csv, json, os, random, sys
import numpy as np, tifffile
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
AL = os.path.join(HERE, "..", "autolabels")
LANCE = "/home/labradorite/g0-splits-project/lance_landmarking/"
SCHEMA = json.load(open(os.path.join(HERE, "..", "landmark_schema.json")))

view, want, n, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
random.seed(int(sys.argv[5]) if len(sys.argv) > 5 else 0)
qc = {r["key"]: r for r in csv.DictReader(open(os.path.join(AL, "qc_final.csv"))) if r["view"] == view}
labs = {r["key"]: r for r in csv.DictReader(open(os.path.join(AL, f"labels_{view}.csv")))}
keys = [k for k, r in qc.items() if r["status"] == want and k in labs]
pick = random.sample(keys, min(n, len(keys)))
pts = SCHEMA["views"][view]["points"]
tiles = []
for k in pick:
    r = labs[k]
    img = Image.fromarray(tifffile.imread(LANCE + r["raw_image"])[..., :3])
    P = {p["id"]: np.array([float(r[p["id"] + "_x"]), float(r[p["id"] + "_y"])]) for p in pts}
    d = ImageDraw.Draw(img)
    for c in SCHEMA["views"][view]["curves"]:
        chain = [c["start"]] + [f"{c['id']}{i + 1}" for i in range(c["n_semilandmarks"])] + [c["end"]]
        if c["id"].endswith(".window"):
            s = view[0]
            tops = [f"{s}{i:02d}" for i in range(12, 17)]
            chain = [c["start"]] + sum([[tops[i], f"{c['id']}{i + 1}"] for i in range(4)], []) + [tops[4], c["end"]]
        d.line([tuple(P[q]) for q in chain], fill=(0, 200, 255), width=3)
    for p in pts:
        x, y = P[p["id"]]
        col = {"anchor": (230, 20, 20), "computed": (170, 0, 200), "semilandmark": (255, 255, 255)}[p["role"]]
        rr = 9 if p["role"] != "semilandmark" else 6
        d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=col, outline="black")
    A = np.array(list(P.values()))
    x0, y0 = A.min(0) - 120
    x1, y1 = A.max(0) + 120
    t = img.crop((int(x0), int(y0), int(x1), int(y1)))
    t.thumbnail((600, 330))
    ImageDraw.Draw(t).text((4, 4), f"{r['group']} {k}  {qc[k]['reason'][:60]}", fill="black")
    tiles.append(t)
cols = 3
W, H = 600, 330
sheet = Image.new("RGB", (W * cols, H * ((len(tiles) + cols - 1) // cols)), "white")
for i, t in enumerate(tiles):
    sheet.paste(t, ((i % cols) * W, (i // cols) * H))
sheet.save(out, quality=88)
