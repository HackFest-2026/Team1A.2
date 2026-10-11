"""Generate the updated 7-page Project Rakshak 2.0 Judge Review Guide PDF.

Fully updated to the present project state, incorporating:
- Split leakage audit (zero data leakage verified across all splits)
- Three-vessel mAP reconciliation (12.75% full holdout, 12.07% edge bench, 12.26% boost study baseline, 16.24% specialist)
- Standardized Jetson roofline intervals (AGX Orin 44.7-48.8 ms / 20.5-22.4 FPS, Orin Nano 134.6-203.1 ms / 4.9-7.4 FPS)
- Analyst workload reduction baseline clarification (Baseline A item-count reduction vs Baseline B negative capacity rows)
- 3 distinct offline procedural map styles (Satellite, Dark Tactical, Terrain) and permanent tactical place names
- Mission Planner interactive OODA execution (zoom, selectable waypoints, animated fly-to, dispatch toast)
- Complete deployment status (12/12 smoke tests, 38/38 pytests, Docker containerization, competition remote sync)
"""

import os
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY


class NumberedCanvas(canvas.Canvas):
    """Canvas that computes total pages and renders running footer."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_footer(num_pages)
            super().showPage()
        super().save()

    def draw_footer(self, page_count):
        self.saveState()
        # Footer rule
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.65)
        self.line(36, 28, 559, 28)

        # Footer Left
        self.setFont("Helvetica-Bold", 7.5)
        self.setFillColor(colors.HexColor("#0f2b48"))
        self.drawString(36, 18, "PROJECT RAKSHAK 2.0 • Judge Review Guide")

        # Footer Right
        self.setFont("Helvetica", 7.5)
        self.setFillColor(colors.HexColor("#64748b"))
        self.drawRightString(559, 18, f"Page {self._pageNumber}")
        self.restoreState()


def make_callout(text, bold_prefix="Judge explanation:", width=523, bg_color="#f8fafc", border_color="#94a3b8"):
    """Render a rounded/bordered callout box matching the Judge Review Guide design."""
    style = ParagraphStyle(
        'CalloutP',
        fontName='Helvetica',
        fontSize=7.8,
        leading=10.6,
        textColor=colors.HexColor("#1e293b")
    )
    p = Paragraph(f"<b>{bold_prefix}</b> “{text}”" if bold_prefix else text, style)
    t = Table([[p]], colWidths=[width])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(bg_color)),
        ('BOX', (0, 0), (-1, -1), 0.65, colors.HexColor(border_color)),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    return t


def build_judge_guide_pdf(output_paths):
    doc_path = str(output_paths[0])
    doc = SimpleDocTemplate(
        doc_path,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=32,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Color definitions
    navy_title   = colors.HexColor("#0f2b48")
    accent_blue  = colors.HexColor("#0369a1")
    text_dark    = colors.HexColor("#1e293b")
    text_muted   = colors.HexColor("#64748b")
    border_slate = colors.HexColor("#cbd5e1")
    header_navy  = colors.HexColor("#102a43")

    # Typography styles
    title_style = ParagraphStyle(
        'DocTitle',
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=navy_title,
        alignment=TA_CENTER
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        fontName='Helvetica',
        fontSize=10.5,
        leading=14,
        textColor=accent_blue,
        alignment=TA_CENTER
    )

    edition_style = ParagraphStyle(
        'DocEdition',
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=text_muted,
        alignment=TA_CENTER
    )

    section_h1 = ParagraphStyle(
        'SectionH1',
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=navy_title,
        spaceBefore=5,
        spaceAfter=2,
        keepWithNext=True
    )

    section_h2 = ParagraphStyle(
        'SectionH2',
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=accent_blue,
        spaceBefore=4,
        spaceAfter=1,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'BodyP',
        fontName='Helvetica',
        fontSize=7.8,
        leading=10.6,
        textColor=text_dark,
        spaceBefore=1,
        spaceAfter=1.5
    )

    bullet_style = ParagraphStyle(
        'BulletP',
        fontName='Helvetica',
        fontSize=7.8,
        leading=10.5,
        textColor=text_dark,
        leftIndent=11,
        firstLineIndent=-7,
        spaceBefore=1.2,
        spaceAfter=1.2
    )

    clarify_style = ParagraphStyle(
        'ClarifyP',
        fontName='Helvetica',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#334155"),
        spaceBefore=2,
        spaceAfter=2
    )

    story = []

    # =========================================================================
    # PAGE 1: COVER & PROJECT SNAPSHOT
    # =========================================================================
    story.append(Spacer(1, 140))
    story.append(Paragraph("PROJECT RAKSHAK 2.0", title_style))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Technical Guidelines, KPI Explainer &amp; Judge Review Guide", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Bullet-point edition • Fully updated to present project state", edition_style))
    story.append(Spacer(1, 40))

    # Snapshot Table
    tbl_hdr = ParagraphStyle('TH', fontName='Helvetica-Bold', fontSize=7.5, leading=9.5, textColor=colors.white)
    tbl_c1  = ParagraphStyle('TC1', fontName='Helvetica-Bold', fontSize=7.5, leading=9.5, textColor=navy_title)
    tbl_c2  = ParagraphStyle('TC2', fontName='Helvetica', fontSize=7.5, leading=10, textColor=text_dark)

    snapshot_data = [
        [Paragraph("PROJECT SNAPSHOT", tbl_hdr), Paragraph("SOURCE-DOCUMENT DETAILS", tbl_hdr)],
        [Paragraph("Hackathon", tbl_c1), Paragraph("KLS Hackfest 2026 — Problem Statement 1A (Naval/Army Geospatial Threat Detection)", tbl_c2)],
        [Paragraph("Team", tbl_c1), Paragraph("Team BotS — KLS Gogte Institute of Technology / KLE Technological University", tbl_c2)],
        [Paragraph("System", tbl_c1), Paragraph("Sovereign dual-domain C4ISR and geospatial threat-intelligence prototype", tbl_c2)],
        [Paragraph("Core idea", tbl_c1), Paragraph("Fuse satellite imagery, SAR/AIS correlations, drone EO/IR, ground sensors and tactical workflows in an offline-first Common Operating Picture.", tbl_c2)],
        [Paragraph("Deployment & Remote", tbl_c1), Paragraph("Air-gapped FastAPI backend + React/Leaflet UI, Dockerized, verified clean on judge repo: HackFest-2026/Team1A.2", tbl_c2)],
        [Paragraph("Audit & Tests", tbl_c1), Paragraph("12/12 Platform Smoke Tests PASSED • 38/38 Pytest Tests PASSED • 0 Outbound Sockets (Zero-Egress Verified)", tbl_c2)]
    ]
    snap_table = Table(snapshot_data, colWidths=[115, 408])
    snap_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), header_navy),
        ('GRID', (0, 0), (-1, -1), 0.5, border_slate),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#f8fafc"), colors.white]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(snap_table)
    story.append(Spacer(1, 14))

    # Important Box
    note_p = Paragraph(
        "<b>Important:</b> figures in this guide are reported directly from canonical evaluation JSON reports "
        "in <code>evaluation/results/</code>, <code>evaluation/RESULTS.md</code>, and <code>PROJECT_OVERVIEW.md</code>. "
        "“Measured”, “simulated”, “computed”, “assumed”, “projected” and “not done” are kept strictly distinct. "
        "This updated edition incorporates the zero-leakage split audit, reconciled vessel mAP benchmarks, "
        "standardized Jetson dense-FP16 roofline intervals, 3 distinct offline map styles, and interactive Mission Planner execution.",
        ParagraphStyle('NoteP', fontName='Helvetica', fontSize=7.6, leading=10.5, textColor=colors.HexColor("#334155"))
    )
    note_tbl = Table([[note_p]], colWidths=[523])
    note_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
        ('BOX', (0, 0), (-1, -1), 0.75, border_slate),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(note_tbl)
    story.append(PageBreak())

    # =========================================================================
    # PAGE 2: HOW TO USE, PROJECT OVERVIEW, VOCABULARY & KPI 1
    # =========================================================================
    story.append(Paragraph("How to use this guide", section_h1))
    story.append(Paragraph("• Use the short “Judge explanation” under each KPI as a plain-language answer during judging.", bullet_style))
    story.append(Paragraph("• Use the evidence bullets to explain what was actually tested and on what hardware/data.", bullet_style))
    story.append(Paragraph("• Never describe a simulated or projected result as a live field result.", bullet_style))
    story.append(Paragraph("• Where the source marks a test “NOT DONE”, say so directly and describe it as future validation.", bullet_style))
    story.append(Paragraph("• Refer to <code>evaluation/RESULTS.md</code> and underlying JSON reports for exact audit provenance.", bullet_style))
    story.append(Spacer(1, 4))

    story.append(Paragraph("Project in one minute", section_h1))
    story.append(Paragraph("• <b>Problem:</b> dark vessels can evade AIS; analysts must inspect large imagery volumes; cloud dependence is unsuitable for disconnected or radio-silent operations.", bullet_style))
    story.append(Paragraph("• <b>Solution:</b> an offline-first, multi-modal COP that combines optical detections, SAR/AIS correlation logic, temporal change detection, drone EO/IR, unattended ground sensors and mission-planning support.", bullet_style))
    story.append(Paragraph("• <b>Security goal:</b> zero external data egress during the audited application-level test; local services communicate strictly over loopback.", bullet_style))
    story.append(Paragraph("• <b>Operational value:</b> consolidate duplicate detections, prioritize alerts, retain queued alerts through simulated link outages and help analysts move from raw sensor data to a reviewable operational picture.", bullet_style))
    story.append(Paragraph("• <b>Prototype boundary:</b> functional, grounded prototype with measured benchmarks and simulated scenarios. Not yet validated by physical sea trials, military radio trials, independent GPS surveys or a human military-staff exercise.", bullet_style))
    story.append(Spacer(1, 4))

    story.append(Paragraph("Status vocabulary", section_h1))
    vocab_data = [
        [Paragraph("Label", tbl_hdr), Paragraph("Meaning for judges", tbl_hdr)],
        [Paragraph("MEASURED", tbl_c1), Paragraph("Timed or evaluated in the stated test environment; does not automatically mean field-validated.", tbl_c2)],
        [Paragraph("SIMULATED", tbl_c1), Paragraph("Produced by a controlled synthetic or Monte Carlo scenario; useful for algorithm testing, not proof of live operational performance.", tbl_c2)],
        [Paragraph("COMPUTED", tbl_c1), Paragraph("Calculated from measured outputs and/or stated assumptions.", tbl_c2)],
        [Paragraph("ASSUMED", tbl_c1), Paragraph("Depends on a modelled baseline or a human-time assumption rather than an observed comparative trial.", tbl_c2)],
        [Paragraph("PROJECTED", tbl_c1), Paragraph("Estimated for hardware or a full pipeline not actually benchmarked end to end.", tbl_c2)],
        [Paragraph("NOT DONE", tbl_c1), Paragraph("No result is available; do not imply validation.", tbl_c2)]
    ]
    vocab_tbl = Table(vocab_data, colWidths=[90, 433])
    vocab_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), header_navy),
        ('GRID', (0, 0), (-1, -1), 0.5, border_slate),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#f8fafc"), colors.white]),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(vocab_tbl)
    story.append(Spacer(1, 4))

    story.append(Paragraph("KPI 1 — Optical detection quality: precision, recall and mAP", section_h1))
    story.append(Paragraph("• Headline overall YOLO11m FP16 results on the held-out validation set: <b>mAP@50 48.46%</b>; mAP@50–95 14.45%; precision 53.78%; recall 48.17%.", bullet_style))
    story.append(Paragraph("• Test scope: 540 tiles, 38 scenes and 66,521 labelled instances. A separate clean maritime holdout contains 21 tiles and 280 vessels across 5 scenes, with 0 training overlap verified.", bullet_style))
    story.append(Paragraph("• Aircraft perform best: <b>mAP@50 89.85%</b>, recall 86.67% (45 ground-truth aircraft). Vehicles: mAP@50 46.83%, recall 52.61%. Infrastructure: mAP@50 44.41%, recall 38.75%.", bullet_style))
    story.append(Paragraph("• Vessels remain the key weakness: generalist mAP@50 <b>12.75%</b> and recall 14.65%; the YOLO11n 1024px specialist reaches mAP@50 <b>16.24%</b> and recall 23.57% on the maritime holdout.", bullet_style))
    story.append(Paragraph("• FP16 overall mAP@50 (48.46%) is close to FP32 (48.37%) and ONNX CPU (47.80%) in the reported tests.", bullet_style))
    story.append(Paragraph("• <b>Zero-Leakage Split Audit:</b> <code>split_overlap_audit.json</code> audited 276 specialist scenes, 301 generalist scenes, 37 <code>val_tune</code> scenes, and 38 <code>val_report</code> scenes. Result: <b>ZERO overlap across all evaluation pairs</b> (disjoint holdout confirmed).", bullet_style))
    story.append(Paragraph("• <b>Reconciled Vessel Numbers:</b> Generalist vessel mAP appears as 12.75% (540 tiles holdout), 12.07% (21 tiles edge bench), and 12.26% (21 tiles boost baseline); 12.75% and 16.24% (specialist) remain the authoritative headline values.", bullet_style))
    story.append(Spacer(1, 2))

    story.append(make_callout(
        "Precision tells us how often a detection is correct; recall tells us how many real labelled objects we find. "
        "mAP summarizes detection quality across confidence thresholds and box overlap requirements. "
        "Our model is stronger for aircraft than small vessels, so we report that limitation honestly rather than presenting one overall score as universal accuracy."
    ))
    story.append(Spacer(1, 2))
    story.append(Paragraph("<b>Be ready to clarify:</b> mAP@50 allows a looser box-overlap threshold than mAP@50–95. Low vessel scores are consistent with small 12–35 pixel objects and class imbalance reported in the source.", clarify_style))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 3: KPI 2, KPI 3, KPI 4, KPI 5 (START)
    # =========================================================================
    story.append(Paragraph("KPI 2 — Dark-vessel detection", section_h1))
    story.append(Paragraph("• Headline end-to-end capture: <b>79.40% ± 2.80%</b>; 95% confidence interval 78.09%–80.71%.", bullet_style))
    story.append(Paragraph("• Post-detection recall: <b>92.63% ± 2.23%</b>; CA-CFAR radar detection rate: <b>85.73% ± 2.65%</b>.", bullet_style))
    story.append(Paragraph("• Reported simulated precision: 100%; false-dark alarm rate: 0%; F1: 0.9616 ± 0.0120.", bullet_style))
    story.append(Paragraph("• Evaluation uses 20 random seeds and 10,000 synthetic contacts per sweep condition; 30% of the synthetic contacts are configured as dark vessels.", bullet_style))
    story.append(Paragraph("• Dead-reckoning matters under timestamp drift: without propagation, false-dark alarms rise to 15.20% at ±5 minutes, 61.08% at ±15 minutes and 77.45% at ±30 minutes in the simulated scenarios.", bullet_style))
    story.append(Paragraph("• Physical sea-trial ground truth: NOT DONE; the source states no local xView3-SAR dataset was present in the repository.", bullet_style))
    story.append(Spacer(1, 2))
    story.append(make_callout(
        "AIS is a cooperative broadcast, so a vessel that stops transmitting may disappear from normal AIS tracking. "
        "This KPI tests whether radar-like SAR detections can be correlated with expected AIS positions to flag possible dark vessels. "
        "The encouraging numbers are simulation results, not a claim of proven live sea performance."
    ))
    story.append(Spacer(1, 4))

    story.append(Paragraph("KPI 3 — Sensor-to-alert latency", section_h1))
    story.append(Paragraph("• YOLO11m single-tile inference on an NVIDIA RTX 4060 Laptop GPU: 34.9 ms mean unboosted; <b>17.85 ± 0.11 ms</b> in the boosted benchmark (P50: 17.37 ms).", bullet_style))
    story.append(Paragraph("• Boosted inference throughput: <b>55.65–56.50 frames/tiles per second</b> for the stated 1024×1024 model configuration.", bullet_style))
    story.append(Paragraph("• Dual-engine YOLO11m + YOLO11n with Weighted Box Fusion: 47.9 ms mean and 20.87 tiles/second.", bullet_style))
    story.append(Paragraph("• Full-scene ingestion across 38 scenes / 540 tiles: mean 1.62 s, median 1.58 s, P95 2.30 s in the reported boosted setup.", bullet_style))
    story.append(Paragraph("• Full end-to-end target below 1.8 s is marked PROJECTED; the source also reports P95 2.30 s and an unboosted estimate around 3.1 s.", bullet_style))
    story.append(Paragraph("• SAR CA-CFAR processing (1.1 s) and SAR-to-AIS matching (85 ms) are described as code-path timings, not logged benchmark measurements.", bullet_style))
    story.append(Spacer(1, 2))
    story.append(make_callout(
        "Latency is the time the system takes to process input; throughput is how many inputs it can process per second. "
        "The fast GPU number is model inference, not the whole journey from raw sensor feed to an alert. "
        "We therefore separate tile timing, full-scene ingestion and the projected full decision pipeline."
    ))
    story.append(Spacer(1, 4))

    story.append(Paragraph("KPI 4 — False alarms and alert pacing", section_h1))
    story.append(Paragraph("• Precision-oriented threshold mode: <b>9.93 unmatched false positives per km²</b> at IoU ≥ 0.3, with 94.75% precision but 17.05% recall.", bullet_style))
    story.append(Paragraph("• F1-oriented mode: 196.83 false positives/km² at IoU ≥ 0.3, with 76.90% precision and 62.36% recall.", bullet_style))
    story.append(Paragraph("• Older thresholds report 49.78 FP/km², 88.59% precision and 36.77% recall at IoU ≥ 0.3.", bullet_style))
    story.append(Paragraph("• At 12 scenes/hour surveillance pacing, the report computes 7.26 high-threat alerts/hour and 149.37 medium-threat alerts/hour; high + medium combined is 156.63/hour.", bullet_style))
    story.append(Paragraph("• 24-hour continuous live-feed false-alarm testing and physical sea-spray/wave-clutter tests: NOT DONE.", bullet_style))
    story.append(Spacer(1, 2))
    story.append(make_callout(
        "This is a trade-off. Raising confidence thresholds reduces false alarms but misses more real objects; "
        "lowering thresholds catches more possible threats but asks analysts to review more false positives. "
        "We can tune the operating point to the mission, but we have not claimed that one setting solves every deployment."
    ))
    story.append(Spacer(1, 4))

    story.append(Paragraph("KPI 5 — Track continuity and ID switches", section_h1))
    story.append(Paragraph("• Tracking combines detections with a constant-velocity Kalman filter in a local ENU coordinate frame and data-association methods including Hungarian, JPDA and nearest-neighbour.", bullet_style))
    story.append(Paragraph("• Clean simulated control: <b>0 ID switches</b>; MOTA 96.08%; MOTP 2.27 m; 96.08% track continuity.", bullet_style))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 4: KPI 5 (CONT), KPI 6, KPI 7, KPI 8 (START)
    # =========================================================================
    story.append(Paragraph("KPI 5 — Track continuity and ID switches (cont.)", section_h1))
    story.append(Paragraph("• Crossing paths: <b>0 ID switches</b> in the stated test; MOTA 92.16%, with MOTP around 9.56–9.99 m.", bullet_style))
    story.append(Paragraph("• During a simulated 60-second AIS dropout: <b>0 ID switches</b> and JPDA MOTA 93.44%.", bullet_style))
    story.append(Paragraph("• Harder chokepoint scenario: JPDA reports 2 ID switches and MOTA 71.22%; Hungarian reports 0 ID switches but MOTA 51.22%.", bullet_style))
    story.append(Paragraph("• Physical field-radar multi-target trials: NOT DONE.", bullet_style))
    story.append(Spacer(1, 2))
    story.append(make_callout(
        "A track ID should keep referring to the same object over time. An ID switch means the tracker accidentally swaps identities. "
        "MOTA summarizes missed detections, false detections and identity errors; MOTP describes position-match precision. "
        "Results are from simulated trajectories, so live radar validation remains future work."
    ))
    story.append(Spacer(1, 4))

    story.append(Paragraph("KPI 6 — Geolocation error (CEP)", section_h1))
    story.append(Paragraph("• Overall, for matched detections at IoU ≥ 0.3: <b>CEP50 0.70 m</b>, <b>CEP90 2.43 m</b>, mean error 1.17 m and RMSE 2.03 m.", bullet_style))
    story.append(Paragraph("• At IoU ≥ 0.3, 37,300 of 66,521 ground-truth objects (56.07%) had matched predictions.", bullet_style))
    story.append(Paragraph("• Vessel subset: CEP50 0.92 m and CEP90 6.54 m, but only 78 of 280 vessels (27.86%) were matched.", bullet_style))
    story.append(Paragraph("• CEP50 is the radius containing 50% of matched localisation errors; CEP90 is the radius containing 90%.", bullet_style))
    story.append(Paragraph("• Important qualification: error is conditional on a bounding-box match and measured against the dataset’s GeoTIFF georeferencing metadata, not independent GPS ground truth.", bullet_style))
    story.append(Paragraph("• Independent differential-GPS survey: NOT DONE.", bullet_style))
    story.append(Spacer(1, 2))
    story.append(make_callout(
        "This KPI asks how close the map coordinate is to the dataset’s georeferenced location. CEP50 of 0.70 m means half of the matched "
        "predictions are within that radius. It does not mean every target is located within 0.70 m, and it does not measure missed targets. "
        "The reference is GeoTIFF metadata, not a field GPS survey."
    ))
    story.append(Spacer(1, 4))

    story.append(Paragraph("KPI 7 — Edge deployment, model size and power", section_h1))
    story.append(Paragraph("• YOLO11m generalist: 20.1 million parameters; FP16 checkpoint 38.7 MB; ONNX export 40.5 MB.", bullet_style))
    story.append(Paragraph("• YOLO11n vessel specialist: 2.6 million parameters (1024px fine-tuned).", bullet_style))
    story.append(Paragraph("• On the RTX 4060 laptop GPU, boosted inference reaches 55.65–56.50 FPS; measured GPU board power during FP16 inference is about 43 W gross and about 30.4–30.8 W net over 12.64 W idle baseline.", bullet_style))
    story.append(Paragraph("• <b>Standardized Dense-FP16 Jetson Roofline Intervals (basis 35.74 ms host, no TensorRT factor):</b>", bullet_style))
    story.append(Paragraph("    - <b>Jetson AGX Orin 64GB:</b> <b>44.7–48.8 ms</b> (<b>20.5–22.4 FPS</b>) [unmeasured, rough estimate only; basis 35.74 ms host].", bullet_style))
    story.append(Paragraph("    - <b>Jetson Orin Nano 8GB:</b> <b>134.6–203.1 ms</b> (<b>4.9–7.4 FPS</b>) [unmeasured, rough estimate only; basis 35.74 ms host].", bullet_style))
    story.append(Paragraph("    - <i>TensorRT may improve this; unmeasured, no Jetson run.</i> All earlier single-point estimates (19.4 ms, 38.2 ms) and 10.8–23.8 ms / 42.0–92.6 FPS intervals are formally superseded.", bullet_style))
    story.append(Paragraph("• All Jetson values are rough projections, not physical measurements. Jetson power measurement is NOT DONE; physical Jetson hardware was not available.", bullet_style))
    story.append(Spacer(1, 2))
    story.append(make_callout(
        "Edge readiness means the model is small and fast enough to be a candidate for local hardware, without relying on cloud inference. "
        "We measured performance on an RTX 4060 laptop. The Jetson numbers are roofline scaling estimates only; "
        "we would need to run the actual model on those boards and measure power before claiming validated embedded performance."
    ))
    story.append(Spacer(1, 4))

    story.append(Paragraph("KPI 8 — Analyst workload reduction and auto-triage", section_h1))
    story.append(Paragraph("• 14,008 raw detections were consolidated into 2,379 spatial entities: <b>83.02% fewer review items</b> after 500m clustering.", bullet_style))
    story.append(Paragraph("• After auto-closing 493 isolated civilian-vehicle entities, 1,886 items remain for human review: <b>86.54% fewer review items</b> than reviewing every raw detection.", bullet_style))
    story.append(Paragraph("• Auto-close rate: 20.72% of consolidated entities. <b>100% of all 493 auto-closed items were isolated civilian vehicles</b>.", bullet_style))
    story.append(Paragraph("• Infrastructure is never auto-closed; vessels and aircraft are routed directly to the priority queue.", bullet_style))
    story.append(Paragraph("• Safety Suite v2: 9/9 critical threat cases escalated (0 missed); 4/4 cooperative vessel controls safely auto-closed; 2/2 ambiguous cases routed to human review.", bullet_style))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 5: KPI 8 (CONT), KPI 9, KPI 10, ZERO-EGRESS AIR GAP
    # =========================================================================
    story.append(Paragraph("KPI 8 — Analyst workload reduction (cont. — Workload baselines)", section_h1))
    story.append(Paragraph("• <b>Baseline A (Manual Raw Detection Review):</b> Reviewing 14,008 raw detections vs 1,886 items yields a measured <b>86.54% reduction</b> across 45–240 s review assumptions (e.g. saving 47.85 hrs/surveillance hour at 45 s/item).", bullet_style))
    story.append(Paragraph("• <b>Baseline B (Fixed 40 min/scene budget = 8.0 hrs/hr cap):</b> Reviewing 595.6 items/hr at ≥60 s requires 9.93h–39.71h, exceeding the fixed 8.0h cap. This explains why rows at 60 s (-24.1%), 120 s (-148.1%), and 240 s (-396.4%) show negative differentials relative to this artificial ceiling.", bullet_style))
    story.append(Paragraph("• Workload-hour savings are COMPUTED using assumed review durations. They are not the result of a human analyst user study.", bullet_style))
    story.append(Spacer(1, 2))
    story.append(make_callout(
        "The key idea is to reduce duplicate boxes and group them into entities before an analyst reviews them. "
        "The 86.54% figure is an item-count reduction, not a measured claim that every analyst will work 86.54% faster. "
        "The safety rules keep vessels, aircraft and infrastructure out of automatic closure; humans remain in the decision loop."
    ))
    story.append(Spacer(1, 4))

    story.append(Paragraph("KPI 9 — Mission-planning cycle and SITREP", section_h1))
    story.append(Paragraph("• Across 30 runs of three tactical defense scenarios, average local REST machine time is <b>0.1843 seconds</b> (Scenario A: 0.257s, Scenario B: 0.140s, Scenario C: 0.156s).", bullet_style))
    story.append(Paragraph("• Operator-paced estimate averages <b>50.19 seconds</b>, including an assumed 50 seconds of operator thinking time.", bullet_style))
    story.append(Paragraph("• Manual baseline averages <b>24 minutes (1440 s)</b>, modelled from a standard five-step military staff procedure.", bullet_style))
    story.append(Paragraph("• Computed cycle-time reduction is <b>96.51% (or 96.5%)</b> using the operator-paced framing, and <b>99.98%</b> for machine REST execution.", bullet_style))
    story.append(Paragraph("• STANAG 2014 SITREP compilation is reported below 50 ms; local BM25 doctrine retrieval below 40 ms.", bullet_style))
    story.append(Paragraph("• Human military-staff exercise and real tactical radio order dissemination: NOT DONE.", bullet_style))
    story.append(Spacer(1, 2))
    story.append(make_callout(
        "The services can assemble a local response quickly, but the headline reduction compares software timings with a modelled manual workflow. "
        "We have not run a controlled study with military staff, so we present 96.51% as a computed estimate rather than observed human performance."
    ))
    story.append(Spacer(1, 4))

    story.append(Paragraph("KPI 10 — DDIL availability and alert survivability", section_h1))
    story.append(Paragraph("• DDIL means denied, disrupted, intermittent or limited communications.", bullet_style))
    story.append(Paragraph("• Simulated 30-minute mission: <b>100% edge detection uptime</b> over 720 alert epochs; 720/720 alerts delivered after store-and-forward; <b>0 lost alerts</b>.", bullet_style))
    story.append(Paragraph("• 13 duplicate packets were handled by sequence-numbered idempotency logic without duplicate ingestion.", bullet_style))
    story.append(Paragraph("• After a simulated 300-second blackout, resynchronisation averages 40.89 seconds at 32 kbps with packet loss; 10.06 seconds at 512 kbps without packet loss.", bullet_style))
    story.append(Paragraph("• Picture availability is 60.36% under a ≤10-second staleness definition, 68.90% under ≤30 seconds and 72.38% under ≤60 seconds.", bullet_style))
    story.append(Paragraph("• Physical combat-net radio trials: NOT DONE.", bullet_style))
    story.append(Spacer(1, 2))
    story.append(make_callout(
        "The prototype queues alerts locally when connectivity is lost and forwards them when the link returns. "
        "The simulation showed no lost alerts, but the Common Operating Picture can still become stale during an outage. "
        "These are software simulations, not proof that a physical military radio network will behave identically."
    ))
    story.append(Spacer(1, 4))

    story.append(Paragraph("Zero-egress air-gap check", section_h1))
    story.append(Paragraph("• Reported audit: <b>0 outbound non-loopback sockets</b>, <b>0 external DNS attempts</b> and <b>0 external CDN/tile references</b> found in a 22-file code scan.", bullet_style))
    story.append(Paragraph("• 40 loopback sockets were monitored; one deliberately triggered socket-guard violation was blocked.", bullet_style))
    story.append(Paragraph("• Verdict in the source: <b>NO_EGRESS_OBSERVED</b>.", bullet_style))
    story.append(Paragraph("• Offline basemap tiles are generated procedurally on localhost; the prototype does not bundle a complete licensed worldwide MBTiles set.", bullet_style))
    story.append(Paragraph("• Scope limitation: application-level socket hooks and psutil monitoring were used. Kernel eBPF tracing and physical hardware network-tap capture are NOT DONE.", bullet_style))
    story.append(Spacer(1, 2))
    story.append(make_callout(
        "Air-gapped here means the audited application test observed no external network egress. We should not overstate the boundary: "
        "this is a user-space audit, not a hardware-certified air-gap assessment. A stronger deployment audit would add kernel-level tracing and physical network capture."
    ))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 6: KPI 11, ARCHITECTURE, LIMITATIONS & DEMO SEQUENCE
    # =========================================================================
    story.append(Paragraph("KPI 11 — Multi-temporal satellite change detection", section_h1))
    story.append(Paragraph("• Purpose: compare two image passes and flag objects that appear, disappear or move after aligning the scenes with ORB + RANSAC.", bullet_style))
    story.append(Paragraph("• Evaluation: 40 synthetic image pairs based on held-out tiles; 120 injected object edits (one new, one removed and one moved per pair), plus structural changes.", bullet_style))
    story.append(Paragraph("• Raw pooled results: precision 20.93%, recall 37.50%, F1 0.2687.", bullet_style))
    story.append(Paragraph("• Stability-filtered pooled results: <b>precision 80.95%</b>, recall 14.17%, F1 0.2411. The filter reduced false positives from 170 to 4 (<b>97.6% reduction</b>) but also missed many changes.", bullet_style))
    story.append(Paragraph("• Mean co-registration error across simulated 0–8 pixel shifts: <b>0.1449 pixels</b>. Structural anomaly capture: 65% of 40 injected examples.", bullet_style))
    story.append(Paragraph("• Real multi-pass satellite sea/land trials: NOT DONE.", bullet_style))
    story.append(Spacer(1, 2))
    story.append(make_callout(
        "The system aligns two images and compares detected objects to find possible changes. The stability filter removes many spurious changes, "
        "improving precision, but recall drops sharply. This is a clear trade-off: fewer false alarms, but more real changes missed. "
        "The reported tests use synthetic edits, so real satellite passes are the next validation step."
    ))
    story.append(Spacer(1, 3))

    story.append(Paragraph("Architecture and platform capabilities at a glance", section_h1))
    story.append(Paragraph("• <b>Multi-Modal Sensors:</b> Sentinel-1 C-band SAR, xView optical imagery, drone EO/IR downlinks, unattended ground sensors (UGS) and AIS streams.", bullet_style))
    story.append(Paragraph("• <b>Dual-Engine AI:</b> YOLO11m generalist (optical) + YOLO11n 1024px vessel specialist fused via Weighted Box Fusion.", bullet_style))
    story.append(Paragraph("• <b>3 Distinct Offline Map Styles:</b> Satellite (dark navy ocean #0a1628, muted land, coastline glow), Dark Tactical (near-black, cyan graticule), Terrain (slate-blue ocean, synthetic elevation shading, watermark) + permanent tactical place names and maritime regions overlay.", bullet_style))
    story.append(Paragraph("• <b>Mission Planner OODA Interactivity:</b> Map zoom controls (+/- buttons, wheel, pinch), selectable intercept waypoints with map pan/highlight, animated dispatch fly-to (<code>map.flyTo</code>, zoom 8-9, 1.5s), marker pulse, and operator toast notifications.", bullet_style))
    story.append(Paragraph("• <b>Local Intelligence & Security:</b> Local BM25 RoE doctrine retrieval, STANAG 2014 SITREP compiler, PBKDF2-200k + JWT authentication, Docker containerized deployment.", bullet_style))
    story.append(Spacer(1, 3))

    story.append(Paragraph("Limitations judges may ask about", section_h1))
    story.append(Paragraph("• Vessel detection is weak compared with aircraft and other classes; specialist improves from 12.75% to 16.24% but remains limited due to small 12–35px sizes and class imbalance.", bullet_style))
    story.append(Paragraph("• Dark-vessel, tracking, DDIL and change-detection figures are simulated rather than physical field trials.", bullet_style))
    story.append(Paragraph("• Jetson performance and power are unmeasured dense-FP16 roofline projections, not physical hardware benchmarks.", bullet_style))
    story.append(Paragraph("• Geolocation uses dataset GeoTIFF georeferencing, not independent differential GPS.", bullet_style))
    story.append(Paragraph("• Workload and mission-cycle reductions depend partly on assumptions; no human analyst or military-staff study has been completed.", bullet_style))
    story.append(Paragraph("• Procedural basemap supports offline operation but is not a complete licensed worldwide map dataset.", bullet_style))
    story.append(Spacer(1, 3))

    story.append(Paragraph("Suggested 3-minute demo sequence", section_h1))
    story.append(Paragraph("• 1. <b>Joint COP Map:</b> Switch between Satellite, Dark Tactical, and Terrain offline styles; show tactical place names and maritime regions.", bullet_style))
    story.append(Paragraph("• 2. <b>Optical Detection:</b> Run detection and show the difference between generalist and vessel-specialist results.", bullet_style))
    story.append(Paragraph("• 3. <b>Dark-Vessel Intercept:</b> Open dark-vessel scenario; explicitly label as simulated and show AIS correlation/dead-reckoning logic.", bullet_style))
    story.append(Paragraph("• 4. <b>Analyst Workload Triage:</b> Show alert consolidation, auto-closed civilian vehicles, priority queue, and 0% missed critical threats.", bullet_style))
    story.append(Paragraph("• 5. <b>DDIL Blackout & Resync:</b> Trigger a simulated link outage, generate alerts, restore connectivity, and show zero-loss resynchronisation.", bullet_style))
    story.append(Paragraph("• 6. <b>Change Detection:</b> Show a two-pass change-detection example and explain the precision/recall trade-off.", bullet_style))
    story.append(Paragraph("• 7. <b>Mission Planner Dispatch:</b> Select an intercept waypoint, click “DISPATCH INTERCEPT MISSION” to trigger fly-to animation, compile STANAG SITREP, and show zero-egress audit proof.", bullet_style))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 7: LIKELY QUESTIONS, SUBMISSION CHECKLIST & SOURCE NOTE
    # =========================================================================
    story.append(Paragraph("Likely judge questions — evidence-based answers", section_h1))

    q_style = ParagraphStyle('QP', fontName='Helvetica-Bold', fontSize=8, leading=10.5, textColor=navy_title, spaceBefore=2, spaceAfter=1)
    a_style = ParagraphStyle('AP', fontName='Helvetica', fontSize=7.6, leading=10.2, textColor=text_dark, leftIndent=8, spaceBefore=0.5, spaceAfter=2.5)

    story.append(Paragraph("Q: Is it production-ready?", q_style))
    story.append(Paragraph("A: No. It is a functional prototype with measured software benchmarks and simulated operational scenarios. Physical sea, radar, radio, GPS and human-staff trials remain.", a_style))

    story.append(Paragraph("Q: Why is vessel recall low?", q_style))
    story.append(Paragraph("A: The source identifies small 12–35 px boxes and class imbalance (280 vessels versus 42,824 infrastructure instances). A specialist model improves recall from 14.65% to 23.57% and mAP from 12.75% to 16.24%. The split audit proved zero data leakage across train, val_tune, and val_report holdout splits.", a_style))

    story.append(Paragraph("Q: Why do three different vessel mAP numbers appear in reports?", q_style))
    story.append(Paragraph("A: They evaluate different scopes and precision modes: 12.75% is the full 540-tile holdout (FP16), 12.07% is the 21-tile maritime holdout in edge_bench, and 12.26% is the 21-tile boost study baseline. Both 12.75% (generalist) and 16.24% (specialist) remain the authoritative headline values.", a_style))

    story.append(Paragraph("Q: What are the Jetson figures based on?", q_style))
    story.append(Paragraph("A: Dense-FP16 roofline scaling from our measured 35.74 ms power-capped host baseline: AGX Orin 44.7–48.8 ms (20.5–22.4 FPS), Orin Nano 134.6–203.1 ms (4.9–7.4 FPS). They are explicitly labeled 'unmeasured, rough estimate only'. TensorRT may improve this; unmeasured, no Jetson run.", a_style))

    story.append(Paragraph("Q: Can you guarantee zero network traffic?", q_style))
    story.append(Paragraph("A: The test observed zero outbound non-loopback sockets and zero external DNS attempts under user-space socket monitoring. Kernel eBPF and hardware packet capture were not done, so we claim “no egress observed in this audit,” not a universal guarantee.", a_style))

    story.append(Paragraph("Q: Are the latency claims end-to-end?", q_style))
    story.append(Paragraph("A: No. Tile inference (17.85 ms) and full-scene ingestion (mean 1.62 s, P95 2.30 s) are measured separately. The <1.8 s full decision-pipeline target is projected.", a_style))

    story.append(Paragraph("Q: Why are some workload reduction numbers negative?", q_style))
    story.append(Paragraph("A: Under Baseline A (manual raw review), Rakshak saves 86.54% review items. Under Baseline B (an arbitrary 40 min/scene cap = 8.0h/hr), reviewing 595.6 items/hr at ≥60s requires 9.93h–39.71h, exceeding a single analyst's 8.0h fixed budget (producing negative capacity differentials: -24.1%, -148.1%, -396.4%).", a_style))

    story.append(Paragraph("Q: What is next?", q_style))
    story.append(Paragraph("A: Prioritize real maritime-labelled data, physical Jetson hardware profiling, live sea/radar trials, independent GPS checks, and a controlled analyst workflow study.", a_style))
    story.append(Spacer(1, 3))

    story.append(Paragraph("Final submission / judging checklist", section_h1))
    story.append(Paragraph("• Bring the raw JSON reports in <code>evaluation/results/</code> that correspond to every KPI and make sure values shown match the report.", bullet_style))
    story.append(Paragraph("• Label every metric as measured, simulated, computed, assumed, projected or not done.", bullet_style))
    story.append(Paragraph("• Keep the vessel limitation, zero-leakage split audit, and change-detection precision/recall trade-off visible.", bullet_style))
    story.append(Paragraph("• State Jetson dense-FP16 roofline intervals (AGX Orin 44.7–48.8 ms, Orin Nano 134.6–203.1 ms) and label them 'unmeasured, rough estimate only'.", bullet_style))
    story.append(Paragraph("• Explain exactly what the zero-egress audit covers (user-space socket hooks) and what it does not cover.", bullet_style))
    story.append(Paragraph("• Separate item-count reduction (86.54%) from assumed analyst-time savings and explain Baseline B negative rows.", bullet_style))
    story.append(Paragraph("• Demonstrate the 3 distinct offline map styles, permanent tactical place names, and interactive Mission Planner dispatch fly-to.", bullet_style))
    story.append(Paragraph("• State that 12/12 smoke tests and 38/38 pytest tests pass, and code is synced on official repo <code>HackFest-2026/Team1A.2.git</code>.", bullet_style))
    story.append(Spacer(1, 4))

    src_p = Paragraph(
        "<b>Source note:</b> This guide was compiled directly from canonical evaluation JSON reports in <code>evaluation/results/</code>, "
        "<code>evaluation/RESULTS.md</code>, and <code>PROJECT_OVERVIEW.md</code>. All KPI values, test scopes, hardware platforms, caveats, and reconciliations "
        "are grounded in actual executed test scripts.",
        ParagraphStyle('SrcNote', fontName='Helvetica-Oblique', fontSize=7, leading=9.5, textColor=text_muted)
    )
    story.append(src_p)

    # Build PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Generated PDF: {doc_path}")

    # Copy to all other destinations
    import shutil
    for p in output_paths[1:]:
        shutil.copyfile(doc_path, str(p))
        print(f"Copied to: {p}")


if __name__ == "__main__":
    targets = [
        Path(r"c:\Users\awhri\Downloads\Project_Rakshak_Updated_Judge_Guide.pdf"),
        Path(r"c:\Users\awhri\OneDrive\Desktop\DEF\Project_Rakshak_Updated_Judge_Guide.pdf"),
        Path(r"c:\Users\awhri\OneDrive\Desktop\DEF\Project_Rakshak_Explainer_Guide.pdf")
    ]
    build_judge_guide_pdf(targets)
