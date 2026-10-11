"""evaluation/eval_vessel_boost.py
================================
Single-pass evaluation on val_report holdout (21 tiles, 280 vessels) for:
1. Baseline Generalist (YOLO11m)
2. Baseline Specialist (YOLO11n)
3. Selected val_tune Winner: Horizontal-flip TTA (1024) fused by WBF (Option d)

Computes P, R, mAP@50, mAP@50-95 and 1,000-resample tile-level Bootstrap 95% Confidence Intervals.
Strictly single-pass: NO retuning after seeing val_report.

Outputs:
  evaluation/results/vessel_boost_report.json
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple
import cv2
import numpy as np
import torch
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "evaluation" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = RESULTS_DIR / "vessel_boost_report.json"

MANIFEST_21 = ROOT / "evaluation" / "val_report_vessel_21_tiles.txt"
LABELS_DIR = ROOT / "runs" / "xview_yolo" / "labels" / "val"
IMAGES_DIR = ROOT / "runs" / "xview_yolo" / "images" / "val"

YOLO11M_WEIGHTS = ROOT / "runs" / "train" / "xview_yolo11m_military" / "weights" / "best.pt"
VESSEL_WEIGHTS = ROOT / "runs" / "train" / "xview_vessel_1024_extended" / "weights" / "best.pt"


def box_iou_np(b1: np.ndarray, b2: np.ndarray) -> np.ndarray:
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


def load_ground_truth_21() -> Tuple[Dict[str, np.ndarray], int]:
    gt_map = {}
    total_gt = 0
    lines = [l.strip() for l in MANIFEST_21.read_text(encoding="utf-8").splitlines() if l.strip()]
    for line in lines:
        stem = Path(line).stem
        lbl = LABELS_DIR / f"{stem}.txt"
        boxes = []
        if lbl.exists():
            for row in lbl.read_text(encoding="utf-8").splitlines():
                parts = row.strip().split()
                if parts and parts[0] == "0":
                    xc, yc, w, h = [float(x) for x in parts[1:5]]
                    x1 = (xc - w / 2.0) * 1024.0
                    y1 = (yc - h / 2.0) * 1024.0
                    x2 = (xc + w / 2.0) * 1024.0
                    y2 = (yc + h / 2.0) * 1024.0
                    boxes.append([x1, y1, x2, y2])
        gt_map[stem] = np.array(boxes) if boxes else np.empty((0, 4))
        total_gt += len(boxes)
    return gt_map, total_gt


def wbf_numpy(boxes_scores: np.ndarray, iou_thresh: float = 0.55, conf_thresh: float = 0.05) -> np.ndarray:
    if len(boxes_scores) == 0:
        return np.empty((0, 5))
    filt = boxes_scores[boxes_scores[:, 4] >= conf_thresh]
    if len(filt) == 0:
        return np.empty((0, 5))
    order = np.argsort(-filt[:, 4])
    filt = filt[order]
    
    clusters = []
    for b in filt:
        box = b[:4]
        conf = b[4]
        matched = False
        for cl in clusters:
            b1 = box
            b2 = cl["weighted_box"]
            xA = max(b1[0], b2[0])
            yA = max(b1[1], b2[1])
            xB = min(b1[2], b2[2])
            yB = min(b1[3], b2[3])
            inter = max(0.0, xB - xA) * max(0.0, yB - yA)
            a1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
            a2 = (b2[2] - b2[0]) * (b2[3] - b2[1])
            denom = a1 + a2 - inter
            iou = inter / denom if denom > 0 else 0.0
            if iou >= iou_thresh:
                cl["boxes"].append(box)
                cl["confs"].append(conf)
                total_w = sum(cl["confs"])
                cl["weighted_box"] = [
                    sum(bb[k] * c for bb, c in zip(cl["boxes"], cl["confs"])) / total_w
                    for k in range(4)
                ]
                matched = True
                break
        if not matched:
            clusters.append({
                "boxes": [box],
                "confs": [conf],
                "weighted_box": list(box)
            })
            
    fused = []
    for cl in clusters:
        box = cl["weighted_box"]
        count = len(cl["confs"])
        conf = max(cl["confs"])
        if count >= 3:
            conf *= 1.35
        elif count >= 2:
            conf *= 1.20
        fused.append([box[0], box[1], box[2], box[3], min(0.99, conf)])
    return np.array(fused) if fused else np.empty((0, 5))


def run_tta_horizontal(model: YOLO, img_bgr: np.ndarray, imgsz: int = 1024, conf: float = 0.05) -> np.ndarray:
    w = img_bgr.shape[1]
    res_orig = model.predict(img_bgr, imgsz=imgsz, conf=conf, device=0, verbose=False)[0]
    boxes_orig = [b[:5] for b in res_orig.boxes.data.cpu().numpy() if int(b[5]) == 0]
    
    img_flip = cv2.flip(img_bgr, 1)
    res_flip = model.predict(img_flip, imgsz=imgsz, conf=conf, device=0, verbose=False)[0]
    boxes_flip = []
    for b in res_flip.boxes.data.cpu().numpy():
        if int(b[5]) == 0:
            x1_new = w - b[2]
            x2_new = w - b[0]
            boxes_flip.append([x1_new, b[1], x2_new, b[3], b[4]])
            
    combined = boxes_orig + boxes_flip
    return np.array(combined) if combined else np.empty((0, 5))


def compute_metrics(
    preds_map: Dict[str, np.ndarray],
    gt_map: Dict[str, np.ndarray],
    tile_subset: List[str] = None,
    iou_thrs: np.ndarray = np.linspace(0.5, 0.95, 10)
) -> Dict[str, float]:
    """Compute mAP@50, mAP@50-95, Precision, Recall on a specific subset of tiles."""
    if tile_subset is None:
        tile_subset = list(gt_map.keys())
        
    total_gts = sum(len(gt_map[s]) for s in tile_subset if s in gt_map)
    if total_gts == 0:
        return {"map50": 0.0, "map50_95": 0.0, "precision": 0.0, "recall": 0.0}
        
    aps = []
    p_at_50, r_at_50 = 0.0, 0.0
    
    for iou_thr in iou_thrs:
        all_tp = []
        all_fp = []
        all_scores = []
        
        for stem in tile_subset:
            gts = gt_map.get(stem, np.empty((0, 4)))
            preds = preds_map.get(stem, np.empty((0, 5)))
            if len(preds) == 0:
                continue
            order = np.argsort(-preds[:, 4])
            p_boxes = preds[order, :4]
            p_scores = preds[order, 4]
            
            if len(gts) == 0:
                for s in p_scores:
                    all_tp.append(0)
                    all_fp.append(1)
                    all_scores.append(s)
                continue
                
            ious = box_iou_np(p_boxes, gts)
            matched_gt = set()
            for p_idx in range(len(p_boxes)):
                gt_idx = np.argmax(ious[p_idx])
                max_iou = ious[p_idx, gt_idx]
                all_scores.append(p_scores[p_idx])
                if max_iou >= iou_thr and gt_idx not in matched_gt:
                    all_tp.append(1)
                    all_fp.append(0)
                    matched_gt.add(gt_idx)
                else:
                    all_tp.append(0)
                    all_fp.append(1)
                    
        if len(all_scores) == 0:
            aps.append(0.0)
            continue
            
        all_tp = np.array(all_tp)
        all_fp = np.array(all_fp)
        all_scores = np.array(all_scores)
        sort_idx = np.argsort(-all_scores)
        tp_cs = np.cumsum(all_tp[sort_idx])
        fp_cs = np.cumsum(all_fp[sort_idx])
        recalls = tp_cs / total_gts
        precisions = tp_cs / (tp_cs + fp_cs)
        
        mrec = np.concatenate(([0.0], recalls, [1.0]))
        mpre = np.concatenate(([1.0], precisions, [0.0]))
        for i in range(len(mpre) - 2, -1, -1):
            mpre[i] = max(mpre[i], mpre[i + 1])
        i = np.where(mrec[1:] != mrec[:-1])[0]
        ap = float(np.sum((mrec[i + 1] - mrec[i]) * mpre[i + 1]))
        aps.append(ap)
        
        if np.isclose(iou_thr, 0.5):
            f1s = 2 * (precisions * recalls) / np.maximum(precisions + recalls, 1e-8)
            best_f1_idx = np.argmax(f1s) if len(f1s) > 0 else 0
            p_at_50 = float(precisions[best_f1_idx]) if len(precisions) > 0 else 0.0
            r_at_50 = float(recalls[best_f1_idx]) if len(recalls) > 0 else 0.0
            
    return {
        "map50": round(float(aps[0]), 4),
        "map50_95": round(float(np.mean(aps)), 4),
        "precision": round(p_at_50, 4),
        "recall": round(r_at_50, 4)
    }


def compute_bootstrap_ci(
    preds_map: Dict[str, np.ndarray],
    gt_map: Dict[str, np.ndarray],
    n_resamples: int = 1000,
    seed: int = 42
) -> Dict[str, Tuple[float, float]]:
    """Compute 95% Bootstrap CI (2.5%, 97.5%) resampled across the 21 tiles."""
    rng = np.random.RandomState(seed)
    tile_list = list(gt_map.keys())
    n_tiles = len(tile_list)
    
    b_map50 = []
    b_map50_95 = []
    b_p = []
    b_r = []
    
    for _ in range(n_resamples):
        sample_indices = rng.choice(n_tiles, size=n_tiles, replace=True)
        # Handle duplicate tile samples with unique aliases
        sample_gt = {}
        sample_pred = {}
        for sample_i, idx in enumerate(sample_indices):
            alias = f"sample_{sample_i}"
            orig_stem = tile_list[idx]
            sample_gt[alias] = gt_map[orig_stem]
            sample_pred[alias] = preds_map.get(orig_stem, np.empty((0, 5)))
            
        m = compute_metrics(sample_pred, sample_gt, tile_subset=list(sample_gt.keys()))
        b_map50.append(m["map50"])
        b_map50_95.append(m["map50_95"])
        b_p.append(m["precision"])
        b_r.append(m["recall"])
        
    def ci_interval(arr):
        return [round(float(np.percentile(arr, 2.5)), 4), round(float(np.percentile(arr, 97.5)), 4)]
        
    return {
        "map50_ci95": ci_interval(b_map50),
        "map50_95_ci95": ci_interval(b_map50_95),
        "precision_ci95": ci_interval(b_p),
        "recall_ci95": ci_interval(b_r)
    }


def main():
    print("=" * 80)
    print("  PROJECT RAKSHAK 2.0 — SINGLE-PASS VESSEL EVALUATION ON VAL_REPORT")
    print("=" * 80)
    
    gt_map, total_gt = load_ground_truth_21()
    tile_stems = list(gt_map.keys())
    print(f"[*] Evaluated Scope: {len(tile_stems)} tiles | {total_gt} GT vessels (val_report holdout)")
    
    # Preload images
    tile_images = {}
    for stem in tile_stems:
        p = IMAGES_DIR / f"{stem}.jpg"
        tile_images[stem] = cv2.imread(str(p))
    print(f"[+] Loaded {len(tile_images)} images into memory.")
    
    # Models
    m_spec = YOLO(str(VESSEL_WEIGHTS))
    m_gen = YOLO(str(YOLO11M_WEIGHTS))
    
    # Warmup
    dummy = np.zeros((1024, 1024, 3), dtype=np.uint8)
    _ = m_spec.predict(dummy, imgsz=1024, conf=0.25, device=0, verbose=False)
    torch.cuda.synchronize()
    
    # 1. Baseline Generalist (YOLO11m @ 1024)
    print("\n[1/3] Inferring Baseline Generalist (YOLO11m @ 1024)...")
    preds_gen = {}
    lat_gen = []
    for stem in tile_stems:
        img = tile_images[stem]
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        res = m_gen.predict(img, imgsz=1024, conf=0.001, device=0, verbose=False)[0]
        b_data = res.boxes.data.cpu().numpy()
        torch.cuda.synchronize()
        t1 = time.perf_counter()
        lat_gen.append((t1 - t0) * 1000.0)
        preds_gen[stem] = b_data[b_data[:, 5] == 0][:, :5] if len(b_data) > 0 else np.empty((0, 5))
        
    metrics_gen = compute_metrics(preds_gen, gt_map)
    ci_gen = compute_bootstrap_ci(preds_gen, gt_map, n_resamples=1000)
    mean_lat_gen = round(float(np.mean(lat_gen)), 2)
    print(f"    Baseline Generalist: mAP@50={metrics_gen['map50']:.4f} [95% CI: {ci_gen['map50_ci95']}], Latency={mean_lat_gen} ms")
    
    # 2. Baseline Specialist (YOLO11n @ 1024)
    print("\n[2/3] Inferring Baseline Specialist (YOLO11n @ 1024)...")
    preds_spec = {}
    lat_spec = []
    for stem in tile_stems:
        img = tile_images[stem]
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        res = m_spec.predict(img, imgsz=1024, conf=0.001, device=0, verbose=False)[0]
        b_data = res.boxes.data.cpu().numpy()
        torch.cuda.synchronize()
        t1 = time.perf_counter()
        lat_spec.append((t1 - t0) * 1000.0)
        preds_spec[stem] = b_data[b_data[:, 5] == 0][:, :5] if len(b_data) > 0 else np.empty((0, 5))
        
    metrics_spec = compute_metrics(preds_spec, gt_map)
    ci_spec = compute_bootstrap_ci(preds_spec, gt_map, n_resamples=1000)
    mean_lat_spec = round(float(np.mean(lat_spec)), 2)
    print(f"    Baseline Specialist: mAP@50={metrics_spec['map50']:.4f} [95% CI: {ci_spec['map50_ci95']}], Latency={mean_lat_spec} ms")
    
    # 3. Winning Config from val_tune: Option d - Horizontal-flip TTA (1024) fused by WBF
    print("\n[3/3] Inferring Winner Config: Horizontal-flip TTA (1024) + WBF (Option d)...")
    preds_boost = {}
    lat_boost = []
    for stem in tile_stems:
        img = tile_images[stem]
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        raw_boxes = run_tta_horizontal(m_spec, img, imgsz=1024, conf=0.05)
        fused = wbf_numpy(raw_boxes, iou_thresh=0.55, conf_thresh=0.05)
        torch.cuda.synchronize()
        t1 = time.perf_counter()
        lat_boost.append((t1 - t0) * 1000.0)
        preds_boost[stem] = fused
        
    metrics_boost = compute_metrics(preds_boost, gt_map)
    ci_boost = compute_bootstrap_ci(preds_boost, gt_map, n_resamples=1000)
    mean_lat_boost = round(float(np.mean(lat_boost)), 2)
    print(f"    Vessel Boost Config: mAP@50={metrics_boost['map50']:.4f} [95% CI: {ci_boost['map50_ci95']}], Latency={mean_lat_boost} ms")
    
    # Compute relative gain
    delta_map50 = round(metrics_boost["map50"] - metrics_spec["map50"], 4)
    rel_gain_pct = round((delta_map50 / max(0.001, metrics_spec["map50"])) * 100.0, 2)
    extra_lat_ms = round(mean_lat_boost - mean_lat_spec, 2)
    
    report = {
        "title": "Project Rakshak 2.0 — Single-Pass Vessel Boost Evaluation on val_report",
        "dataset_scope": "5 scenes / 21 tiles / 280 vessels (strictly val_report holdout)",
        "hardware": torch.cuda.get_device_name(0),
        "provenance": "MEASURED",
        "bootstrap_resamples": 1000,
        "tuning_note": "Tuning performed strictly on val_tune (40 tiles); single-pass evaluation on val_report without retuning.",
        "baseline_generalist_yolo11m": {
            "model": "YOLO11m (20.1M params)",
            "imgsz": 1024,
            "metrics": metrics_gen,
            "bootstrap_ci95": ci_gen,
            "latency_ms": {"mean": mean_lat_gen, "p50": round(float(np.median(lat_gen)), 2)}
        },
        "baseline_specialist_yolo11n": {
            "model": "YOLO11n Vessel Specialist (2.6M params)",
            "imgsz": 1024,
            "metrics": metrics_spec,
            "bootstrap_ci95": ci_spec,
            "latency_ms": {"mean": mean_lat_spec, "p50": round(float(np.median(lat_spec)), 2)}
        },
        "vessel_boost_winner_option_d": {
            "config": "Horizontal-flip TTA (1024) fused by Weighted Box Fusion (WBF IoU=0.55, conf=0.05)",
            "model": "YOLO11n Vessel Specialist",
            "metrics": metrics_boost,
            "bootstrap_ci95": ci_boost,
            "latency_ms": {"mean": mean_lat_boost, "p50": round(float(np.median(lat_boost)), 2)},
            "comparison_to_baseline_specialist": {
                "delta_map50": delta_map50,
                "relative_gain_pct": f"+{rel_gain_pct}%" if rel_gain_pct >= 0 else f"{rel_gain_pct}%",
                "extra_latency_ms": extra_lat_ms
            }
        }
    }
    
    OUTPUT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n[+] Saved official evaluation report to: {OUTPUT_FILE}")
    
    print("\n" + "=" * 90)
    print("  FINAL EVALUATION COMPARISON ON VAL_REPORT (21 TILES / 280 VESSELS)")
    print("=" * 90)
    print(f"{'Model / Configuration':<32} | {'mAP@50 (95% CI)':<24} | {'mAP@50-95':<10} | {'P':<6} | {'R':<6} | {'Latency':<8}")
    print("-" * 90)
    print(f"{'Generalist (YOLO11m baseline)':<32} | {metrics_gen['map50']:.4f} {ci_gen['map50_ci95']} | {metrics_gen['map50_95']:.4f}     | {metrics_gen['precision']:.4f} | {metrics_gen['recall']:.4f} | {mean_lat_gen:<6.1f}ms")
    print(f"{'Specialist (YOLO11n baseline)':<32} | {metrics_spec['map50']:.4f} {ci_spec['map50_ci95']} | {metrics_spec['map50_95']:.4f}     | {metrics_spec['precision']:.4f} | {metrics_spec['recall']:.4f} | {mean_lat_spec:<6.1f}ms")
    print(f"{'Vessel Boost (TTA + WBF)':<32} | {metrics_boost['map50']:.4f} {ci_boost['map50_ci95']} | {metrics_boost['map50_95']:.4f}     | {metrics_boost['precision']:.4f} | {metrics_boost['recall']:.4f} | {mean_lat_boost:<6.1f}ms")
    print("=" * 90)
    print(f"Delta over specialist baseline: {delta_map50:+.4f} ({rel_gain_pct:+.2f}%) | Extra Latency: {extra_lat_ms:+.1f} ms")


if __name__ == "__main__":
    main()
