"""Write landmark_schema.json (machine-readable protocol) from scheme.py."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from scheme import SCHEME  # noqa: E402

out = {"protocol": "Neodiprion lance landmarking protocol v1", "views": {}}
for view, s in SCHEME.items():
    pts, order = [], 0
    for name, a in s["anchors"].items():
        pts.append(dict(id=name, role="anchor", type=a["type"], definition=a["name"],
                        on_outline=a["snap"], old_protocol_point=a["old"]))
    for name, c in s["computed"].items():
        pts.append(dict(id=name, role="computed", type=c["type"], definition=c["name"]))
    curves = []
    for c in s["curves"]:
        ends = [c["from"], c["to"]] if c["path"] == "outline" else [c["through"][0], c["through"][-1]]
        curves.append(dict(id=c["name"], path=c["path"], start=ends[0], end=ends[1], n_semilandmarks=c["n"],
                           old_protocol_points_reused=c.get("slide_old", [])))
        for k in range(c["n"]):
            pts.append(dict(id=f"{c['name']}{k + 1}", role="semilandmark", type="semi", curve=c["name"]))
    out["views"][view] = dict(
        n_points=len(pts),
        n_anchors=len(s["anchors"]),
        n_computed=len(s["computed"]),
        n_semilandmarks=sum(c["n"] for c in s["curves"]),
        points=pts,
        curves=curves,
        old_points_retired=s["dropped_old"],
    )
json.dump(out, open(os.path.join(os.path.dirname(__file__), "..", "landmark_schema.json"), "w"), indent=1)
print({v: (d["n_points"], d["n_anchors"], d["n_computed"], d["n_semilandmarks"]) for v, d in out["views"].items()})
