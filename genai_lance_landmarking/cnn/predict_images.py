"""Run a trained landmark model on a set of images and write its predictions.

The images come from a manifest (any protocol); only its image paths are used.
The number of landmarks is read from the checkpoint, so old- and new-protocol
models run the same way.

usage: python predict_images.py --angle Right --checkpoint best.pt --manifest m.csv
                                [--keys keys.txt] --out predictions.csv
Output: key, group, then x1, y1, x2, y2, ... in original-image pixels.
"""
import argparse, csv, os, sys
from pathlib import Path

MODEL = "/home/labradorite/g0-splits-project/lance_landmarking/model"
sys.path.insert(0, MODEL)
import torch  # noqa: E402
from torch.utils.data import DataLoader  # noqa: E402
from constants import HEATMAP_STRIDE  # noqa: E402
from dataset import LanceLandmarkDataset  # noqa: E402
from heatmap import dsnt_expectation  # noqa: E402
from model import HeatmapNet  # noqa: E402
from splits import load_clean_samples  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--angle", required=True)
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--keys", help="file with one manifest key per line; default: all images of this angle")
    ap.add_argument("--out", required=True)
    ap.add_argument("--batch-size", type=int, default=8)
    a = ap.parse_args()
    torch.set_num_threads(int(os.environ.get("OMP_NUM_THREADS", os.cpu_count() or 1)))
    samples = load_clean_samples(a.manifest, a.angle)
    if a.keys:
        keep = set(Path(a.keys).read_text().split())
        samples = [s for s in samples if s.key in keep]
    state = torch.load(a.checkpoint, map_location="cpu")
    # the last conv layer's output channels = number of landmarks
    n = [v.shape[0] for k, v in state.items() if k.endswith("weight") and v.dim() == 4][-1]
    model = HeatmapNet(n, pretrained=False)
    model.load_state_dict(state)
    model.eval()
    loader = DataLoader(LanceLandmarkDataset(samples), batch_size=a.batch_size, shuffle=False, num_workers=0)
    rows = []
    with torch.no_grad():
        for batch in loader:
            xy = dsnt_expectation(model(batch["image"]))[0] * HEATMAP_STRIDE  # input-image px
            for b in range(len(batch["key"])):
                px0, py0 = batch["pad"][b].tolist()
                orig = ((xy[b] - torch.tensor([px0, py0])) / batch["scale"][b].item()).tolist()
                rows.append([batch["key"][b], batch["group"][b]] + [round(v, 2) for p in orig for v in p])
    with open(a.out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["key", "group"] + [f"{c}{i + 1}" for i in range(n) for c in "xy"])
        w.writerows(rows)
    print(f"{a.angle}: {len(rows)} images, {n} landmarks -> {a.out}")


if __name__ == "__main__":
    main()
