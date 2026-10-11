"""evaluation/tune_vessel_inference.py
===================================
Systematic inference-only tuning for vessel detection on val_tune (40 tiles, 169 vessels).
Tuning strictly on val_tune; val_report is completely held out.

Configurations evaluated:
1. Baseline: Specialist at imgsz 1024
2. Baseline: Generalist at imgsz 1024
3. Option a: Specialist upscaled to imgsz 1280 & imgsz 1536
4. Option b: Sliced inference (SAHI style) with slices 512 & 640 (25% overlap)
5. Option c: Confidence sweep (0.05 - 0.40) & WBF IoU (0.5, 0.6, 0.7)
6. Option d: Horizontal-flip TTA fused by WBF
7. Option e: Specialist + Generalist dual-model fusion
8. Combinations:
   - Specialist (1280) + Generalist (1024) + WBF
   - Specialist (1280) + Horizontal-flip TTA + WBF
   - Specialist (1280) + Generalist (1024) + Horizontal-flip TTA + WBF

Outputs:
  evaluation/results/vessel_tuning_val_tune.json
"""

import copy
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
OUTPUT_FILE = RESULTS_DIR / "vessel_tuning_val_tune.json"

MANIFEST_TUNE = ROOT / "evaluation" / "val_tune_vessel_tiles.txt"
LABELS_DIR = ROOT / "runs" / "xview_yolo" / "labels" / "val"
IMAGES_DIR = ROOT / "runs" / "xview_yolo" / "images" / "val"

YOLO11M_WEIGHTS = ROOT / "runs" / "train" / "xview_yolo11m_military" / "weights" / "best.pt"
VESSEL_WEIGHTS = ROOT / "runs" / "train" / "xview_vessel_1024_extended" / "weights" / "best.pt"


def box_iou_np(b1: np.ndarray, b2: np.ndarray) -> np.ndarray:
    """Pairwise IoU matrix between b1 (N, 4) and b2 (M, 4)."""
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


def load_val_tune_ground_truth() -> Tuple[Dict[str, np.ndarray], int]:
    """Load GT boxes for all 40 val_tune vessel tiles."""
    gt_map = {}
    total_gt = 0
    lines = [l.strip() for l in MANIFEST_TUNE.read_text(encoding="utf-8").splitlines() if l.strip()]
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


def compute_map50(preds_map: Dict[str, np.ndarray], gt_map: Dict[str, np.ndarray]) -> Dict[str, float]:
    """Compute standard mAP@50 and F1-optimal Precision/Recall."""
    total_gts = sum(len(v) for v in gt_map.values())
    all_tp = []
    all_fp = []
    all_scores = []
    for stem, gts in gt_map.items():
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
            if max_iou >= 0.5 and gt_idx not in matched_gt:
                all_tp.append(1)
                all_fp.append(0)
                matched_gt.add(gt_idx)
            else:
                all_tp.append(0)
                all_fp.append(1)
    if len(all_scores) == 0:
        return {"map50": 0.0, "precision": 0.0, "recall": 0.0}
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
    f1s = 2 * (precisions * recalls) / np.maximum(precisions + recalls, 1e-8)
    best_f1_idx = np.argmax(f1s) if len(f1s) > 0 else 0
    p = float(precisions[best_f1_idx]) if len(precisions) > 0 else 0.0
    r = float(recalls[best_f1_idx]) if len(recalls) > 0 else 0.0
    return {"map50": round(ap, 4), "precision": round(p, 4), "recall": round(r, 4)}


def wbf_numpy(boxes_scores: np.ndarray, iou_thresh: float = 0.55, conf_thresh: float = 0.05) -> np.ndarray:
    """Numpy implementation of Weighted Box Fusion for single class."""
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
            # IoU between current box and cluster weighted box
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
                # Recompute weighted box
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


def run_sahi_slices(model: YOLO, img_bgr: np.ndarray, slice_size: int = 512, overlap: float = 0.25, conf: float = 0.05) -> np.ndarray:
    """Run SAHI-style sliding window inference on slices plus full image."""
    h, w = img_bgr.shape[:2]
    stride = int(slice_size * (1.0 - overlap))
    
    xs = list(range(0, max(1, w - slice_size + 1), stride))
    ys = list(range(0, max(1, h - slice_size + 1), stride))
    if not xs or xs[-1] + slice_size < w:
        xs.append(max(0, w - slice_size))
    if not ys or ys[-1] + slice_size < h:
        ys.append(max(0, h - slice_size))
        
    all_boxes = []
    # 1. Full image context
    res_full = model.predict(img_bgr, imgsz=1024, conf=conf, device=0, verbose=False)[0]
    for b in res_full.boxes.data.cpu().numpy():
        if int(b[5]) == 0:
            all_boxes.append(b[:5])
            
    # 2. Slices
    for y in ys:
        for x in xs:
            crop = img_bgr[y:y+slice_size, x:x+slice_size]
            res_crop = model.predict(crop, imgsz=slice_size, conf=conf, device=0, verbose=False)[0]
            for b in res_crop.boxes.data.cpu().numpy():
                if int(b[5]) == 0:
                    box_offset = [b[0] + x, b[1] + y, b[2] + x, b[3] + y, b[4]]
                    all_boxes.append(box_offset)
                    
    return np.array(all_boxes) if all_boxes else np.empty((0, 5))


def run_tta_horizontal(model: YOLO, img_bgr: np.ndarray, imgsz: int = 1024, conf: float = 0.05) -> np.ndarray:
    """Run horizontal flip test-time augmentation."""
    w = img_bgr.shape[1]
    res_orig = model.predict(img_bgr, imgsz=imgsz, conf=conf, device=0, verbose=False)[0]
    boxes_orig = [b[:5] for b in res_orig.boxes.data.cpu().numpy() if int(b[5]) == 0]
    
    # Flip
    img_flip = cv2.flip(img_bgr, 1)
    res_flip = model.predict(img_flip, imgsz=imgsz, conf=conf, device=0, verbose=False)[0]
    boxes_flip = []
    for b in res_flip.boxes.data.cpu().numpy():
        if int(b[5]) == 0:
            # Invert horizontal coordinates: x1_orig = w - x2_flip, x2_orig = w - x1_flip
            x1_new = w - b[2]
            x2_new = w - b[0]
            boxes_flip.append([x1_new, b[1], x2_new, b[3], b[4]])
            
    combined = boxes_orig + boxes_flip
    return np.array(combined) if combined else np.empty((0, 5))


def main():
    print("=" * 75)
    print("  PROJECT RAKSHAK 2.0 — VESSEL INFERENCE TUNING ON VAL_TUNE")
    print("=" * 75)
    
    gt_map, total_gt = load_val_tune_ground_truth()
    tile_stems = list(gt_map.keys())
    print(f"[*] Calibration set: {len(tile_stems)} tiles | {total_gt} GT vessels")
    
    # Preload images into memory for fair, pure inference timing
    print("[*] Loading tile images into memory...")
    tile_images = {}
    for stem in tile_stems:
        p = IMAGES_DIR / f"{stem}.jpg"
        tile_images[stem] = cv2.imread(str(p))
    print(f"[+] Loaded {len(tile_images)} images into memory.")
    
    # Load models
    m_spec = YOLO(str(VESSEL_WEIGHTS))
    m_gen = YOLO(str(YOLO11M_WEIGHTS))
    
    configs = [
        {"id": "baseline_spec_1024", "name": "Specialist (imgsz=1024, baseline)", "type": "single", "model": "spec", "imgsz": 1024, "conf": 0.001, "wbf": False},
        {"id": "baseline_gen_1024", "name": "Generalist (imgsz=1024, baseline)", "type": "single", "model": "gen", "imgsz": 1024, "conf": 0.001, "wbf": False},
        # a. Specialist upscaling
        {"id": "spec_imgsz_1280", "name": "Option a: Specialist at imgsz=1280", "type": "single", "model": "spec", "imgsz": 1280, "conf": 0.001, "wbf": False},
        {"id": "spec_imgsz_1536", "name": "Option a: Specialist at imgsz=1536", "type": "single", "model": "spec", "imgsz": 1536, "conf": 0.001, "wbf": False},
        # b. SAHI slices
        {"id": "spec_sahi_512", "name": "Option b: SAHI slices 512 (overlap 25%)", "type": "sahi", "slice": 512, "conf": 0.05, "wbf_iou": 0.55},
        {"id": "spec_sahi_640", "name": "Option b: SAHI slices 640 (overlap 25%)", "type": "sahi", "slice": 640, "conf": 0.05, "wbf_iou": 0.55},
        # c. Confidence sweep & WBF IoU (using baseline specialist)
        {"id": "spec_conf_010_wbf_050", "name": "Option c: Conf=0.10, WBF IoU=0.50", "type": "wbf_sweep", "conf": 0.10, "wbf_iou": 0.50},
        {"id": "spec_conf_015_wbf_060", "name": "Option c: Conf=0.15, WBF IoU=0.60", "type": "wbf_sweep", "conf": 0.15, "wbf_iou": 0.60},
        {"id": "spec_conf_020_wbf_070", "name": "Option c: Conf=0.20, WBF IoU=0.70", "type": "wbf_sweep", "conf": 0.20, "wbf_iou": 0.70},
        # d. Horizontal flip TTA
        {"id": "spec_tta_hflip_1024", "name": "Option d: Horizontal-flip TTA (1024)", "type": "tta", "imgsz": 1024, "conf": 0.05, "wbf_iou": 0.55},
        {"id": "spec_tta_hflip_1280", "name": "Option d: Horizontal-flip TTA (1280)", "type": "tta", "imgsz": 1280, "conf": 0.05, "wbf_iou": 0.55},
        # e. Specialist + Generalist Dual-Model Fusion
        {"id": "fusion_spec1024_gen1024", "name": "Option e: Dual-Model Fusion (Spec 1024 + Gen 1024)", "type": "dual", "spec_imgsz": 1024, "gen_imgsz": 1024, "conf": 0.05, "wbf_iou": 0.55},
        {"id": "fusion_spec1280_gen1024", "name": "Option e: Dual-Model Fusion (Spec 1280 + Gen 1024)", "type": "dual", "spec_imgsz": 1280, "gen_imgsz": 1024, "conf": 0.05, "wbf_iou": 0.55},
        # Combinations
        {"id": "combo_spec1280_gen1024_tta", "name": "Combo: Spec 1280 (TTA) + Gen 1024 + WBF", "type": "combo_full", "wbf_iou": 0.55, "conf": 0.05},
        {"id": "combo_spec1536_gen1024_wbf", "name": "Combo: Spec 1536 + Gen 1024 + WBF", "type": "dual", "spec_imgsz": 1536, "gen_imgsz": 1024, "conf": 0.05, "wbf_iou": 0.55},
    ]
    
    results = []
    
    for cfg in configs:
        print(f"\n[*] Evaluating: {cfg['name']}...")
        preds_all = {}
        latencies = []
        
        # Warmup GPU
        dummy = np.zeros((1024, 1024, 3), dtype=np.uint8)
        _ = m_spec.predict(dummy, imgsz=1024, conf=0.25, device=0, verbose=False)
        torch.cuda.synchronize()
        
        for stem in tile_stems:
            img = tile_images[stem]
            torch.cuda.synchronize()
            t0 = time.perf_counter()
            
            c_type = cfg["type"]
            if c_type == "single":
                m = m_spec if cfg["model"] == "spec" else m_gen
                res = m.predict(img, imgsz=cfg["imgsz"], conf=cfg["conf"], device=0, verbose=False)[0]
                b_raw = res.boxes.data.cpu().numpy()
                boxes = b_raw[b_raw[:, 5] == 0][:, :5] if len(b_raw) > 0 else np.empty((0, 5))
                
            elif c_type == "sahi":
                boxes_raw = run_sahi_slices(m_spec, img, slice_size=cfg["slice"], overlap=0.25, conf=cfg["conf"])
                boxes = wbf_numpy(boxes_raw, iou_thresh=cfg["wbf_iou"], conf_thresh=cfg["conf"])
                
            elif c_type == "wbf_sweep":
                res = m_spec.predict(img, imgsz=1024, conf=0.001, device=0, verbose=False)[0]
                b_raw = res.boxes.data.cpu().numpy()
                boxes_raw = b_raw[b_raw[:, 5] == 0][:, :5] if len(b_raw) > 0 else np.empty((0, 5))
                boxes = wbf_numpy(boxes_raw, iou_thresh=cfg["wbf_iou"], conf_thresh=cfg["conf"])
                
            elif c_type == "tta":
                boxes_raw = run_tta_horizontal(m_spec, img, imgsz=cfg["imgsz"], conf=cfg["conf"])
                boxes = wbf_numpy(boxes_raw, iou_thresh=cfg["wbf_iou"], conf_thresh=cfg["conf"])
                
            elif c_type == "dual":
                res_s = m_spec.predict(img, imgsz=cfg["spec_imgsz"], conf=cfg["conf"], device=0, verbose=False)[0]
                b_s = res_s.boxes.data.cpu().numpy()
                boxes_s = b_s[b_s[:, 5] == 0][:, :5] if len(b_s) > 0 else np.empty((0, 5))
                
                res_g = m_gen.predict(img, imgsz=cfg["gen_imgsz"], conf=cfg["conf"], device=0, verbose=False)[0]
                b_g = res_g.boxes.data.cpu().numpy()
                boxes_g = b_g[b_g[:, 5] == 0][:, :5] if len(b_g) > 0 else np.empty((0, 5))
                
                combined = np.vstack([boxes_s, boxes_g]) if (len(boxes_s) > 0 and len(boxes_g) > 0) else (boxes_s if len(boxes_s) > 0 else boxes_g)
                boxes = wbf_numpy(combined, iou_thresh=cfg["wbf_iou"], conf_thresh=cfg["conf"])
                
            elif c_type == "combo_full":
                # Spec 1280 with TTA + Gen 1024 fused by WBF
                boxes_s = run_tta_horizontal(m_spec, img, imgsz=1280, conf=cfg["conf"])
                res_g = m_gen.predict(img, imgsz=1024, conf=cfg["conf"], device=0, verbose=False)[0]
                b_g = res_g.boxes.data.cpu().numpy()
                boxes_g = b_g[b_g[:, 5] == 0][:, :5] if len(b_g) > 0 else np.empty((0, 5))
                combined = np.vstack([boxes_s, boxes_g]) if (len(boxes_s) > 0 and len(boxes_g) > 0) else (boxes_s if len(boxes_s) > 0 else boxes_g)
                boxes = wbf_numpy(combined, iou_thresh=cfg["wbf_iou"], conf_thresh=cfg["conf"])
                
            torch.cuda.synchronize()
            t1 = time.perf_counter()
            latencies.append((t1 - t0) * 1000.0)
            preds_all[stem] = boxes
            
        metrics = compute_map50(preds_all, gt_map)
        mean_lat = round(float(np.mean(latencies)), 2)
        p50_lat = round(float(np.median(latencies)), 2)
        
        entry = {
            "id": cfg["id"],
            "name": cfg["name"],
            "map50": metrics["map50"],
            "precision": metrics["precision"],
            "recall": metrics["recall"],
            "mean_latency_ms": mean_lat,
            "p50_latency_ms": p50_lat,
            "config_details": cfg
        }
        results.append(entry)
        print(f"    --> mAP@50: {metrics['map50']:.4f} | P: {metrics['precision']:.4f} | R: {metrics['recall']:.4f} | Latency: {mean_lat} ms/tile")
        
    # Sort results by mAP@50 descending
    results.sort(key=lambda x: x["map50"], reverse=True)
    best_cfg = results[0]
    
    report = {
        "title": "Project Rakshak 2.0 — Vessel Inference Tuning on val_tune",
        "dataset_scope": "40 tiles / 169 vessels (strictly val_tune partition, zero overlap with val_report)",
        "hardware": torch.cuda.get_device_name(0),
        "total_configs_evaluated": len(results),
        "winning_config": best_cfg,
        "all_ranked_configs": results
    }
    
    OUTPUT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("\n" + "=" * 80)
    print("  VAL_TUNE RANKING SUMMARY (SORTED BY mAP@50)")
    print("=" * 80)
    print(f"{'Rank':<4} | {'Configuration Name':<45} | {'mAP@50':<8} | {'P':<6} | {'R':<6} | {'Latency':<8}")
    print("-" * 80)
    for rank, r in enumerate(results, start=1):
        star = " ★ (WINNER)" if rank == 1 else ""
        print(f"{rank:<4} | {r['name']:<45} | {r['map50']:<8.4f} | {r['precision']:<6.4f} | {r['recall']:<6.4f} | {r['mean_latency_ms']:<6.1f}ms{star}")
    print("=" * 80)
    print(f"\n[+] Full tuning report saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
