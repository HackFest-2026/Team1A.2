"""evaluation/vessel_diagnose.py
==============================
Diagnostic analysis of vessel ground-truth and detection performance across pixel-size buckets on val_report holdout.

Metrics computed on val_report holdout (21 tiles, 280 GT vessels):
1. GT distribution across pixel size buckets (<8, 8-12, 12-20, 20-40, >40 px).
2. Per-bucket count, recall (IoU >= 0.5), and mean IoU for:
   - YOLO11m Generalist (xview_yolo11m_military)
   - YOLO11n Vessel Specialist (xview_vessel_1024_extended)
3. Average vessels per tile.
4. Count of GT boxes overlapping another GT box at IoU > 0.3.
Outputs:
   evaluation/results/vessel_diagnosis.json
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
import numpy as np
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "evaluation" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = RESULTS_DIR / "vessel_diagnosis.json"

MANIFEST_21 = ROOT / "evaluation" / "val_report_vessel_21_tiles.txt"
LABELS_DIR = ROOT / "runs" / "xview_yolo" / "labels" / "val"
IMAGES_DIR = ROOT / "runs" / "xview_yolo" / "images" / "val"

YOLO11M_WEIGHTS = ROOT / "runs" / "train" / "xview_yolo11m_military" / "weights" / "best.pt"
VESSEL_WEIGHTS = ROOT / "runs" / "train" / "xview_vessel_1024_extended" / "weights" / "best.pt"

SIZE_BUCKETS = [
    ("<8", 0.0, 8.0),
    ("8-12", 8.0, 12.0),
    ("12-20", 12.0, 20.0),
    ("20-40", 20.0, 40.0),
    (">40", 40.0, float("inf")),
]


def box_iou(b1: np.ndarray, b2: np.ndarray) -> np.ndarray:
    """Compute pairwise IoU matrix between b1 (N, 4) and b2 (M, 4) in [x1, y1, x2, y2]."""
    if len(b1) == 0 or len(b2) == 0:
        return np.zeros((len(b1), len(b2)), dtype=np.float32)
    tl = np.maximum(b1[:, None, :2], b2[None, :, :2])
    br = np.minimum(b1[:, None, 2:], b2[None, :, 2:])
    wh = np.clip(br - tl, 0, None)
    inter = wh[:, :, 0] * wh[:, :, 1]
    a1 = (b1[:, 2] - b1[:, 0]) * (b1[:, 3] - b1[:, 1])
    a2 = (b2[:, 2] - b2[:, 0]) * (b2[:, 3] - b2[:, 1])
    union = a1[:, None] + a2[None, :] - inter
    return np.where(union > 0, inter / union, 0.0)


def load_ground_truth() -> Dict[str, List[Dict[str, Any]]]:
    """Load GT vessel boxes for the 21 tiles."""
    tile_gts = {}
    lines = [l.strip() for l in MANIFEST_21.read_text(encoding="utf-8").splitlines() if l.strip()]
    for line in lines:
        stem = Path(line).stem
        lbl_file = LABELS_DIR / f"{stem}.txt"
        boxes = []
        if lbl_file.exists():
            for row in lbl_file.read_text(encoding="utf-8").splitlines():
                parts = row.strip().split()
                if parts and parts[0] == "0":  # Vessel
                    xc, yc, w, h = [float(x) for x in parts[1:5]]
                    w_px = w * 1024.0
                    h_px = h * 1024.0
                    x1 = (xc - w / 2.0) * 1024.0
                    y1 = (yc - h / 2.0) * 1024.0
                    x2 = (xc + w / 2.0) * 1024.0
                    y2 = (yc + h / 2.0) * 1024.0
                    max_dim = max(w_px, h_px)
                    boxes.append({
                        "stem": stem,
                        "box_xyxy": [x1, y1, x2, y2],
                        "w_px": round(w_px, 2),
                        "h_px": round(h_px, 2),
                        "max_dim_px": round(max_dim, 2),
                        "area_px": round(w_px * h_px, 2)
                    })
        tile_gts[stem] = boxes
    return tile_gts


def get_bucket_name(dim: float) -> str:
    for name, low, high in SIZE_BUCKETS:
        if low <= dim < high:
            return name
    return ">40"


def evaluate_model_on_buckets(
    model: YOLO,
    tile_gts: Dict[str, List[Dict[str, Any]]],
    conf_thresh: float = 0.25,
    is_generalist: bool = False
) -> Dict[str, Any]:
    """Evaluate recall and mean IoU per pixel size bucket for a given model."""
    bucket_stats = {name: {"gt_count": 0, "matched_count": 0, "ious": []} for name, _, _ in SIZE_BUCKETS}
    
    for stem, gts in tile_gts.items():
        img_path = IMAGES_DIR / f"{stem}.jpg"
        results = model.predict(str(img_path), imgsz=1024, conf=conf_thresh, device=0, verbose=False)[0]
        
        preds = []
        for box in results.boxes:
            cls_id = int(box.cls[0].item())
            if (is_generalist and cls_id == 0) or (not is_generalist and cls_id == 0):
                preds.append(box.xyxy[0].cpu().numpy())
        
        if not gts:
            continue
            
        gt_boxes = np.array([g["box_xyxy"] for g in gts])
        pred_boxes = np.array(preds) if preds else np.empty((0, 4))
        
        if len(pred_boxes) > 0:
            iou_mat = box_iou(gt_boxes, pred_boxes)  # (num_gt, num_pred)
            max_ious = np.max(iou_mat, axis=1)
        else:
            max_ious = np.zeros(len(gt_boxes))
            
        for g_idx, g in enumerate(gts):
            b_name = get_bucket_name(g["max_dim_px"])
            bucket_stats[b_name]["gt_count"] += 1
            best_iou = float(max_ious[g_idx])
            bucket_stats[b_name]["ious"].append(best_iou)
            if best_iou >= 0.5:
                bucket_stats[b_name]["matched_count"] += 1
                
    summary = {}
    for name, _, _ in SIZE_BUCKETS:
        cnt = bucket_stats[name]["gt_count"]
        matched = bucket_stats[name]["matched_count"]
        recall = round(matched / cnt, 4) if cnt > 0 else 0.0
        ious = bucket_stats[name]["ious"]
        mean_iou_all = round(float(np.mean(ious)), 4) if ious else 0.0
        matched_ious = [iou for iou in ious if iou >= 0.5]
        mean_iou_matched = round(float(np.mean(matched_ious)), 4) if matched_ious else 0.0
        summary[name] = {
            "gt_count": cnt,
            "matched_count": matched,
            "recall": recall,
            "mean_iou_all_gt": mean_iou_all,
            "mean_iou_matched": mean_iou_matched,
        }
    return summary


def main():
    print("=" * 70)
    print("  PROJECT RAKSHAK 2.0 — VESSEL GROUND TRUTH & MODEL DIAGNOSTIC")
    print("=" * 70)
    
    tile_gts = load_ground_truth()
    all_gts = [g for sub in tile_gts.values() for g in sub]
    total_gts = len(all_gts)
    num_tiles = len(tile_gts)
    avg_vessels_per_tile = round(total_gts / num_tiles, 2)
    
    print(f"[*] Total Ground Truth Vessels : {total_gts}")
    print(f"[*] Total Evaluated Tiles     : {num_tiles}")
    print(f"[*] Average Vessels Per Tile   : {avg_vessels_per_tile}")
    
    # GT Overlap check at IoU > 0.3
    overlapping_gt_count = 0
    overlapping_pairs = []
    for stem, gts in tile_gts.items():
        if len(gts) < 2:
            continue
        gt_boxes = np.array([g["box_xyxy"] for g in gts])
        iou_mat = box_iou(gt_boxes, gt_boxes)
        np.fill_diagonal(iou_mat, 0.0)
        overlaps = np.where(iou_mat > 0.3)
        overlapping_gt_indices = set(overlaps[0])
        overlapping_gt_count += len(overlapping_gt_indices)
        if len(overlapping_gt_indices) > 0:
            overlapping_pairs.append({
                "tile": stem,
                "count": len(overlapping_gt_indices),
                "pairs": [(int(i), int(j), round(float(iou_mat[i, j]), 3)) for i, j in zip(overlaps[0], overlaps[1]) if i < j]
            })
            
    print(f"[*] GT Boxes Overlapping Another GT (IoU > 0.3): {overlapping_gt_count}")
    
    # Bucket distribution of GT
    bucket_counts = {name: 0 for name, _, _ in SIZE_BUCKETS}
    for g in all_gts:
        bucket_counts[get_bucket_name(g["max_dim_px"])] += 1
    print("\n[*] GT Size Distribution by max(w, h):")
    for name, cnt in bucket_counts.items():
        pct = round((cnt / total_gts) * 100.0, 1)
        print(f"    Bucket {name:<8}: {cnt:>3} boxes ({pct:>5.1f}%)")
        
    # Evaluate YOLO11m Generalist
    print("\n[*] Evaluating YOLO11m Generalist (conf >= 0.25)...")
    m_gen = YOLO(str(YOLO11M_WEIGHTS))
    gen_diag = evaluate_model_on_buckets(m_gen, tile_gts, conf_thresh=0.25, is_generalist=True)
    
    # Evaluate YOLO11n Specialist
    print("[*] Evaluating YOLO11n Specialist (conf >= 0.25)...")
    m_spec = YOLO(str(VESSEL_WEIGHTS))
    spec_diag = evaluate_model_on_buckets(m_spec, tile_gts, conf_thresh=0.25, is_generalist=False)
    
    # Also evaluate unthresholded (conf >= 0.05) to see raw detector reach
    print("[*] Evaluating YOLO11m Generalist (conf >= 0.05)...")
    gen_diag_05 = evaluate_model_on_buckets(m_gen, tile_gts, conf_thresh=0.05, is_generalist=True)
    print("[*] Evaluating YOLO11n Specialist (conf >= 0.05)...")
    spec_diag_05 = evaluate_model_on_buckets(m_spec, tile_gts, conf_thresh=0.05, is_generalist=False)
    
    output = {
        "title": "Project Rakshak 2.0 — Vessel Detection Diagnosis on val_report",
        "dataset_scope": f"{num_tiles} tiles / {total_gts} vessels",
        "total_gt_vessels": total_gts,
        "total_tiles": num_tiles,
        "avg_vessels_per_tile": avg_vessels_per_tile,
        "gt_overlapping_another_gt_iou_gt_0_3": {
            "count": overlapping_gt_count,
            "percentage_of_gt": round((overlapping_gt_count / total_gts) * 100.0, 2),
            "details": overlapping_pairs
        },
        "gt_bucket_distribution": bucket_counts,
        "yolo11m_generalist_conf_0_25": gen_diag,
        "yolo11n_specialist_conf_0_25": spec_diag,
        "yolo11m_generalist_conf_0_05": gen_diag_05,
        "yolo11n_specialist_conf_0_05": spec_diag_05,
    }
    
    OUTPUT_FILE.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"\n[+] Saved diagnosis report to: {OUTPUT_FILE}")
    
    # Print comparison table
    print("\n" + "=" * 80)
    print(f"{'Bucket':<8} | {'GT Count':<8} | {'Generalist R (@0.25)':<20} | {'Specialist R (@0.25)':<20} | {'Generalist Mean IoU':<18} | {'Specialist Mean IoU':<18}")
    print("-" * 80)
    for name, _, _ in SIZE_BUCKETS:
        cnt = bucket_counts[name]
        g_rec = gen_diag[name]["recall"]
        s_rec = spec_diag[name]["recall"]
        g_iou = gen_diag[name]["mean_iou_all_gt"]
        s_iou = spec_diag[name]["mean_iou_all_gt"]
        print(f"{name:<8} | {cnt:<8} | {g_rec:<20.4f} | {s_rec:<20.4f} | {g_iou:<18.4f} | {s_iou:<18.4f}")
    print("=" * 80)


if __name__ == "__main__":
    main()
