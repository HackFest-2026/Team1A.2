import base64
import os
import subprocess
from pathlib import Path
from pypdf import PdfReader

# Paths
WORKSPACE = Path(r"c:\Users\awhri\OneDrive\Desktop\DEF")
IMAGE_PATH = Path(r"C:\Users\awhri\.gemini\antigravity\brain\0ea8c42e-8c4b-47f9-90b5-1a2e8465094d\.user_uploaded\media_1791668398356_a304a8bf.png")
OUTPUT_HTML = WORKSPACE / "team_dossier.html"
OUTPUT_PDF = WORKSPACE / "Project_Rakshak_Team_Contributions_Judges_Dossier.pdf"
EDGE_EXE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")

# Base64 encode image
img_base64 = ""
if IMAGE_PATH.exists():
    with open(IMAGE_PATH, "rb") as f:
        img_base64 = base64.b64encode(f.read()).decode("utf-8")

html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Project Rakshak 2.0 - Team BotS Engineering Contributions Dossier</title>
<style>
  @page {{
    size: A4 portrait;
    margin: 10mm 12mm 10mm 12mm;
  }}

  * {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }}

  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #1e293b;
    background-color: #ffffff;
    font-size: 8.8pt;
    line-height: 1.4;
  }}

  /* Page Wrapper */
  .page {{
    width: 100%;
    height: 100%;
    page-break-after: always;
    break-after: page;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }}

  .page:last-child {{
    page-break-after: auto;
    break-after: auto;
  }}

  .page-content {{
    flex: 1;
  }}

  /* Primary Header Section */
  .header {{
    background: linear-gradient(135deg, #091224 0%, #102a43 100%);
    color: #ffffff;
    padding: 12px 16px;
    border-radius: 6px;
    margin-bottom: 10px;
    border-bottom: 3px solid #00d2ff;
  }}

  .top-badges {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
  }}

  .badge-tag {{
    font-size: 7pt;
    font-weight: 700;
    letter-spacing: 0.6px;
    text-transform: uppercase;
    padding: 2px 7px;
    border-radius: 3px;
    display: inline-block;
  }}

  .badge-classification {{
    background: rgba(239, 68, 68, 0.25);
    color: #fca5a5;
    border: 1px solid rgba(239, 68, 68, 0.45);
  }}

  .badge-hackathon {{
    background: rgba(0, 210, 255, 0.2);
    color: #7dd3fc;
    border: 1px solid rgba(0, 210, 255, 0.45);
  }}

  .header h1 {{
    font-size: 17pt;
    font-weight: 800;
    letter-spacing: -0.2px;
    color: #ffffff;
    margin-bottom: 1px;
  }}

  .header h1 span {{
    color: #00d2ff;
  }}

  .header-subtitle {{
    font-size: 8.5pt;
    color: #94a3b8;
    font-weight: 500;
    margin-bottom: 8px;
  }}

  .header-meta {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 7.2pt;
    color: #cbd5e1;
    border-top: 1px solid rgba(255, 255, 255, 0.15);
    padding-top: 6px;
  }}

  /* Running Header on Pages 2 & 3 */
  .running-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #091224;
    color: #ffffff;
    padding: 7px 12px;
    border-radius: 5px;
    margin-bottom: 10px;
    border-left: 3px solid #00d2ff;
    font-size: 7.5pt;
  }}

  .running-header .title {{
    font-weight: 700;
    letter-spacing: 0.4px;
    color: #ffffff;
  }}

  .running-header .sub {{
    color: #94a3b8;
  }}

  /* Team Graphic Banner */
  .team-img-banner {{
    margin: 6px 0 10px 0;
    text-align: center;
    background: #050b14;
    border-radius: 6px;
    padding: 5px;
    border: 1px solid #1e293b;
  }}

  .team-img-banner img {{
    max-width: 100%;
    height: 56px;
    object-fit: contain;
    display: inline-block;
  }}

  /* Executive Note Box */
  .executive-box {{
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-left: 3px solid #0284c7;
    border-radius: 5px;
    padding: 8px 12px;
    margin-bottom: 10px;
    font-size: 7.8pt;
    color: #334155;
    line-height: 1.35;
  }}

  .executive-box strong {{
    color: #0f172a;
  }}

  /* Section Title */
  .section-title {{
    font-size: 9.5pt;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #0f172a;
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 8px;
    padding-bottom: 3px;
    border-bottom: 2px solid #e2e8f0;
  }}

  .section-title::before {{
    content: "";
    display: inline-block;
    width: 5px;
    height: 12px;
    background: #0284c7;
    border-radius: 2px;
  }}

  /* Member Cards */
  .member-card {{
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 10px 12px;
    margin-bottom: 9px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
    border-left: 4px solid #0369a1;
  }}

  .member-card.c-vision {{ border-left-color: #0284c7; }}
  .member-card.c-tiling {{ border-left-color: #0d9488; }}
  .member-card.c-radar {{ border-left-color: #4f46e5; }}
  .member-card.c-threat {{ border-left-color: #dc2626; }}
  .member-card.c-c2 {{ border-left-color: #d97706; }}
  .member-card.c-rag {{ border-left-color: #7c3aed; }}

  .card-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
    padding-bottom: 4px;
    border-bottom: 1px dashed #e2e8f0;
  }}

  .card-title-group {{
    display: flex;
    align-items: baseline;
    gap: 8px;
  }}

  .member-name {{
    font-size: 10pt;
    font-weight: 800;
    color: #0f172a;
    letter-spacing: 0.2px;
  }}

  .member-role {{
    font-size: 7.5pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #0284c7;
  }}

  .pillar-tag {{
    font-size: 6.8pt;
    font-weight: 700;
    text-transform: uppercase;
    background: #f1f5f9;
    color: #475569;
    padding: 2px 5px;
    border-radius: 3px;
    border: 1px solid #cbd5e1;
  }}

  /* Bullet points */
  .card-bullets {{
    list-style: none;
    margin-bottom: 6px;
  }}

  .card-bullets li {{
    position: relative;
    padding-left: 12px;
    margin-bottom: 4px;
    font-size: 7.8pt;
    line-height: 1.34;
    color: #334155;
  }}

  .card-bullets li::before {{
    content: "▪";
    position: absolute;
    left: 1px;
    color: #0284c7;
    font-size: 8pt;
  }}

  .card-bullets li strong {{
    color: #0f172a;
    font-weight: 700;
  }}

  /* Metrics row */
  .metrics-row {{
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-top: 5px;
    padding-top: 5px;
    border-top: 1px solid #f1f5f9;
  }}

  .metric-pill {{
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 3px;
    padding: 2px 6px;
    font-size: 6.8pt;
    font-family: Consolas, "Courier New", monospace;
    font-weight: 600;
    color: #0f172a;
    display: inline-flex;
    align-items: center;
    gap: 3px;
  }}

  .metric-pill .lbl {{
    color: #64748b;
    font-weight: 500;
  }}

  .metric-pill .val {{
    color: #0284c7;
    font-weight: 700;
  }}

  /* Architecture Deep Dive Box (Page 2) */
  .deep-dive-box {{
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-left: 3px solid #4f46e5;
    border-radius: 5px;
    padding: 8px 12px;
    margin-top: 8px;
    font-size: 7.5pt;
    color: #334155;
    line-height: 1.35;
  }}

  .deep-dive-box strong {{
    color: #0f172a;
  }}

  /* Tables */
  table.dossier-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 7.2pt;
    margin-bottom: 8px;
    background: #ffffff;
    border: 1px solid #cbd5e1;
  }}

  table.dossier-table th {{
    background: #0f172a;
    color: #f8fafc;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    padding: 4px 6px;
    text-align: left;
    border: 1px solid #334155;
  }}

  table.dossier-table td {{
    padding: 4px 6px;
    border: 1px solid #e2e8f0;
    color: #334155;
    vertical-align: middle;
  }}

  table.dossier-table tr:nth-child(even) {{
    background: #f8fafc;
  }}

  .mono {{
    font-family: Consolas, monospace;
    font-weight: 600;
  }}

  .highlight-val {{
    font-weight: 700;
    color: #0369a1;
  }}

  /* Footer */
  .footer {{
    margin-top: 6px;
    padding-top: 4px;
    border-top: 1px solid #e2e8f0;
    display: flex;
    justify-content: space-between;
    font-size: 6.8pt;
    color: #64748b;
  }}

  /* Quote Box */
  .quote-box {{
    background: #091224;
    color: #e2e8f0;
    padding: 8px 12px;
    border-radius: 5px;
    font-size: 7.6pt;
    font-style: italic;
    border-left: 3px solid #00d2ff;
    margin-top: 6px;
    line-height: 1.35;
  }}

  .quote-box strong {{
    color: #00d2ff;
    font-style: normal;
  }}
</style>
</head>
<body>

  <!-- ==================== PAGE 1 ==================== -->
  <div class="page">
    <div class="page-content">
      <div class="header">
        <div class="top-badges">
          <span class="badge-tag badge-classification">CLASSIFIED: SOVEREIGN DEFENSE PROTOTYPE // 100% AIR-GAPPED</span>
          <span class="badge-tag badge-hackathon">KLS HACKFEST 2026 // PROBLEM STATEMENT 1A</span>
        </div>
        <h1>PROJECT RAKSHAK <span>2.0</span></h1>
        <div class="header-subtitle">Sovereign Dual-Domain C4ISR & Multi-Modal Geospatial Threat Intelligence Platform</div>
        <div class="header-meta">
          <span><strong>ENGINEERING UNIT:</strong> TEAM BOTS (KLS GIT / KLE TECH)</span>
          <span><strong>TARGET ENVELOPE:</strong> EMCON-ALPHA (ZERO CLOUD EGRESS)</span>
          <span><strong>BENCHMARK BASIS:</strong> VERIFIABLE RAW JSON AUDIT</span>
        </div>
      </div>

      <div class="team-img-banner">
        <img src="data:image/png;base64,{img_base64}" alt="Team Members // Team BotS" />
      </div>

      <div class="executive-box">
        <strong>Executive Note for Technical Judges:</strong> Project Rakshak 2.0 addresses high-threat littoral and northern border operations where forces operate under electronic warfare radio silence (EMCON) and denied communications (DDIL). Every architectural module below was individually engineered and benchmarked by the designated team member. All figures reflect raw, verifiable evaluation reports stored in <code>evaluation/results/</code>.
      </div>

      <div class="section-title">Pillar I: Tactical Vision & Geospatial Slicing Engineering</div>

      <!-- MEMBER 1: ADITYA BAJANTRI -->
      <div class="member-card c-vision">
        <div class="card-header">
          <div class="card-title-group">
            <span class="member-name">ADITYA BAJANTRI</span>
            <span class="member-role">LEAD / VISION SYSTEMS</span>
          </div>
          <span class="pillar-tag">System Architect & Computer Vision</span>
        </div>
        <ul class="card-bullets">
          <li><strong>System Architecture & Sovereign Air-Gap:</strong> Directed the 4-tier C4ISR platform architecture, enforcing strict zero-egress boundaries (0 non-loopback sockets, 0 external DNS queries, verified via <code>egress_test_report.json</code>).</li>
          <li><strong>Dual-Model Satellite Computer Vision:</strong> Trained and fine-tuned dual optical detection models (YOLO11m 20.1M generalist + YOLO11n 2.6M specialist) on 0.3m GSD sub-meter satellite imagery (xView), achieving <strong>48.46% overall mAP@50</strong> and <strong>89.85% mAP@50 on aircraft</strong>.</li>
          <li><strong>Ensemble & Edge Acceleration:</strong> Engineered Weighted Box Fusion (WBF) and FP16 CUDA/TensorRT acceleration, clocking <strong>17.85 ms inference latency (~56 FPS)</strong> on host tactical GPU hardware.</li>
          <li><strong>Multi-Temporal Satellite Change Detection:</strong> Built the bi-temporal change detection pipeline combining ORB feature extraction and RANSAC sub-pixel co-registration (<strong>&lt;0.15 px registration error</strong>) with Hungarian bipartite matching to autonomously detect added, removed, and relocated military assets.</li>
        </ul>
        <div class="metrics-row">
          <span class="metric-pill"><span class="lbl">Primary Model:</span> <span class="val">YOLO11m (20.1M)</span></span>
          <span class="metric-pill"><span class="lbl">Aircraft mAP@50:</span> <span class="val">89.85%</span></span>
          <span class="metric-pill"><span class="lbl">Boosted Latency:</span> <span class="val">17.85 ± 0.11 ms</span></span>
          <span class="metric-pill"><span class="lbl">Co-Registration:</span> <span class="val">0.1449 px Error</span></span>
          <span class="metric-pill"><span class="lbl">Network Egress:</span> <span class="val">0 Bytes (Air-Gapped)</span></span>
        </div>
      </div>

      <!-- MEMBER 2: GAGAN BONGALE -->
      <div class="member-card c-tiling">
        <div class="card-header">
          <div class="card-title-group">
            <span class="member-name">GAGAN BONGALE</span>
            <span class="member-role">DATA TILING & GEOSPATIAL PIPELINE</span>
          </div>
          <span class="pillar-tag">Large-Scale Geospatial Ingestion</span>
        </div>
        <ul class="card-bullets">
          <li><strong>Sliced Geospatial Inference (SAHI):</strong> Engineered the sliced tiling engine to ingest and process multi-gigabyte satellite scenes and large-format GeoTIFFs without memory overflow or compute bottlenecks.</li>
          <li><strong>Dynamic 1024×1024 Overlapping Slicer:</strong> Engineered the sliding-window slicing algorithm with overlap compensation, specifically calibrated to preserve small, low-pixel-footprint tactical targets (12–35 px maritime craft).</li>
          <li><strong>Coordinate Transformation & Georeferencing:</strong> Converted raw pixel bounding boxes to real-world UTM and WGS84 geographic coordinates, achieving sub-meter ground localisation accuracy (<strong>CEP50 of 0.70 m</strong>, <strong>CEP90 of 2.43 m</strong>).</li>
          <li><strong>Air-Gapped Procedural Basemaps & Data Balancing:</strong> Developed local offline vector tile generation (<code>tile_service.py</code>) eliminating external Mapbox/OSM calls, along with class-weighted sampling algorithms to resolve severe training set imbalances.</li>
        </ul>
        <div class="metrics-row">
          <span class="metric-pill"><span class="lbl">Tiling Window:</span> <span class="val">1024×1024 Overlapping</span></span>
          <span class="metric-pill"><span class="lbl">Localisation Accuracy:</span> <span class="val">0.70 m CEP50</span></span>
          <span class="metric-pill"><span class="lbl">CEP90 Precision:</span> <span class="val">2.43 m</span></span>
          <span class="metric-pill"><span class="lbl">Scene Ingestion:</span> <span class="val">1.62 s / Scene</span></span>
          <span class="metric-pill"><span class="lbl">Basemaps:</span> <span class="val">100% Procedural Offline</span></span>
        </div>
      </div>
    </div>

    <div class="footer">
      <span>Project Rakshak 2.0 // Team BotS Technical Evaluation Dossier</span>
      <span>Page 1 of 3</span>
    </div>
  </div>

  <!-- ==================== PAGE 2 ==================== -->
  <div class="page">
    <div class="page-content">
      <div class="running-header">
        <span class="title">PROJECT RAKSHAK 2.0 — TECHNICAL EVALUATION DOSSIER</span>
        <span class="sub">PILLAR II: MULTI-SENSOR FUSION & KINEMATIC THREAT TRACKING</span>
      </div>

      <div class="section-title">Pillar II: Radar / AIS Cross-Correlation & Kinematic Threat Tracking</div>

      <!-- MEMBER 3: UTSAV NANAPUR -->
      <div class="member-card c-radar">
        <div class="card-header">
          <div class="card-title-group">
            <span class="member-name">UTSAV NANAPUR</span>
            <span class="member-role">RADAR / AIS STREAM FUSION</span>
          </div>
          <span class="pillar-tag">Spaceborne SAR & Maritime Intelligence</span>
        </div>
        <ul class="card-bullets">
          <li><strong>Sentinel-1 SAR Radar Processing:</strong> Developed the spaceborne Synthetic Aperture Radar (SAR C-Band) detection engine using a 2D CA-CFAR (Cell-Averaging Constant False Alarm Rate) algorithm that screens 25,000 radar cells in <strong>1.1 seconds</strong>.</li>
          <li><strong>Kinematic AIS Dead-Reckoning:</strong> Ingested live maritime AIS transponder feeds and implemented Dead-Reckoning (SOG/COG) temporal projection to maintain accurate target correlation across ±5 to ±30-minute sensor time offsets.</li>
          <li><strong>Dark Vessel Interception:</strong> Automated Haversine great-circle spatial cross-matching (<strong>85 ms latency</strong>) between SAR radar contacts and AIS positions, achieving a <strong>79.40% headline capture rate</strong> of non-broadcasting / dark vessels with <strong>100% precision</strong>.</li>
          <li><strong>Naval Hull Classification:</strong> Implemented physical waterline length estimation to automatically categorize radar contacts into defense naval classes (Skiffs, Patrol Trawlers, Corvettes, Frigates, and Capital Ships).</li>
        </ul>
        <div class="metrics-row">
          <span class="metric-pill"><span class="lbl">SAR Algorithm:</span> <span class="val">2D CA-CFAR</span></span>
          <span class="metric-pill"><span class="lbl">Processing Time:</span> <span class="val">1.1 s (25k Cells)</span></span>
          <span class="metric-pill"><span class="lbl">Matching Latency:</span> <span class="val">85 ms</span></span>
          <span class="metric-pill"><span class="lbl">Dark Capture Rate:</span> <span class="val">79.40 ± 2.80%</span></span>
          <span class="metric-pill"><span class="lbl">Alert Precision:</span> <span class="val">100.0% (0 False Darks)</span></span>
        </div>
      </div>

      <!-- MEMBER 4: MISBAH FALAK -->
      <div class="member-card c-threat">
        <div class="card-header">
          <div class="card-title-group">
            <span class="member-name">MISBAH FALAK</span>
            <span class="member-role">KINEMATICS / THREAT & AUTO-TRIAGE</span>
          </div>
          <span class="pillar-tag">Multi-Target Tracking & Threat Scoring</span>
        </div>
        <ul class="card-bullets">
          <li><strong>Multi-Sensor Kinematic Tracking:</strong> Implemented a Constant-Velocity Kalman Filter in a local ENU frame fusing multi-sensor covariances (AIS &sigma;=12m, Optical &sigma;=25m, SAR &sigma;=65m).</li>
          <li><strong>Track Association & Zero ID-Switches:</strong> Implemented Joint Probabilistic Data Association (JPDA) and Hungarian bipartite gating, maintaining <strong>0 track ID switches</strong> through 60-second AIS blackouts and sharp 90° tactical evasion maneuvers.</li>
          <li><strong>Deterministic Tactical Threat Matrix:</strong> Formulated the real-time threat evaluation engine (0–100 scoring) calculating kinematic vectors, radar cross-sections, transponder status, and proximity to sensitive military perimeters (e.g., Mumbai ODA, Border Sector Alpha).</li>
          <li><strong>Analyst Cognitive Workload Reduction:</strong> Designed 500m spatial entity clustering and rule-based auto-triage, delivering an <strong>86.54% reduction in items requiring manual human review</strong> with <strong>0.0% missed critical threats</strong>.</li>
        </ul>
        <div class="metrics-row">
          <span class="metric-pill"><span class="lbl">Tracking Filter:</span> <span class="val">CV Kalman + JPDA</span></span>
          <span class="metric-pill"><span class="lbl">ID Switches:</span> <span class="val">0 (Evasion Turns)</span></span>
          <span class="metric-pill"><span class="lbl">Item Reduction:</span> <span class="val">86.54% (14k → 1.8k)</span></span>
          <span class="metric-pill"><span class="lbl">Auto-Close Benign:</span> <span class="val">20.72%</span></span>
          <span class="metric-pill"><span class="lbl">Missed Threats:</span> <span class="val">0.0% (Safety Suite v2)</span></span>
        </div>
      </div>

      <!-- ARCHITECTURAL INTEGRATION NOTE (PILLAR II DEEP DIVE) -->
      <div class="deep-dive-box">
        <strong>Cross-Sensor Kinematic Fusion Architecture:</strong> Radar hits extracted by Utsav's CA-CFAR engine are cross-correlated against dead-reckoned AIS transponders. Contacts exhibiting spatial dissonance (&gt;2.0 km discrepancy) or completely absent transponder signatures are flagged as <em>Dark Vessels</em>. Misbah's tracking engine ingests these entities, assigns a persistent Kalman state vector, and runs dynamic threat-scoring against defined exclusion perimeters (e.g., offshore oil platforms or border defense zones).
      </div>
    </div>

    <div class="footer">
      <span>Project Rakshak 2.0 // Team BotS Technical Evaluation Dossier</span>
      <span>Page 2 of 3</span>
    </div>
  </div>

  <!-- ==================== PAGE 3 ==================== -->
  <div class="page">
    <div class="page-content">
      <div class="running-header">
        <span class="title">PROJECT RAKSHAK 2.0 — TECHNICAL EVALUATION DOSSIER</span>
        <span class="sub">PILLAR III: COMMAND INTERFACE, AUTONOMOUS DOCTRINE & THE OODA LOOP</span>
      </div>

      <div class="section-title">Pillar III: Tactical C2 Visualization & Autonomous Military Doctrine</div>

      <!-- MEMBER 5: SHALINA MANIYAR -->
      <div class="member-card c-c2">
        <div class="card-header">
          <div class="card-title-group">
            <span class="member-name">SHALINA MANIYAR</span>
            <span class="member-role">C2 INTERFACE & COMMON OPERATING PICTURE</span>
          </div>
          <span class="pillar-tag">Tactical GIS & Command Dashboard</span>
        </div>
        <ul class="card-bullets">
          <li><strong>Tactical Command & Control (C2) Frontend:</strong> Designed and built the military Common Operating Picture (COP) using React, Vite, and TypeScript for real-time situational awareness.</li>
          <li><strong>Zero-Egress Vector GIS Engine:</strong> Engineered an air-gapped SVG/Canvas geospatial rendering system (<code>world_land.json</code>, <code>offlineGeoData.ts</code>), completely removing external tile server calls to prevent RF and DNS signature leakage.</li>
          <li><strong>Role-Based Operational Workspaces:</strong> Delivered tailored views for <strong>Tactical Analysts</strong> (split-screen triage queues, one-click dark vessel adjudication, target fly-to inspection) and <strong>Commanders</strong> (tactical heatmaps, zone breach alerts, and intercept dispatching).</li>
          <li><strong>Mission Dispatch & Telemetry Display:</strong> Implemented real-time sensor-to-screen telemetry streaming, threat priority queuing, and interactive waypoint routing for field units and patrol craft.</li>
        </ul>
        <div class="metrics-row">
          <span class="metric-pill"><span class="lbl">Tech Stack:</span> <span class="val">React 18 / Vite / TypeScript</span></span>
          <span class="metric-pill"><span class="lbl">Map Engine:</span> <span class="val">100% Offline SVG/Canvas</span></span>
          <span class="metric-pill"><span class="lbl">Triage Queues:</span> <span class="val">Priority vs Review</span></span>
          <span class="metric-pill"><span class="lbl">External Calls:</span> <span class="val">0 (No OSM/Mapbox)</span></span>
        </div>
      </div>

      <!-- MEMBER 6: NIYATI GOGRI -->
      <div class="member-card c-rag">
        <div class="card-header">
          <div class="card-title-group">
            <span class="member-name">NIYATI GOGRI</span>
            <span class="member-role">STANAG SITREP & SOVEREIGN DOCTRINE RAG</span>
          </div>
          <span class="pillar-tag">Defense Intelligence & OODA Optimization</span>
        </div>
        <ul class="card-bullets">
          <li><strong>Air-Gapped Defense Doctrine RAG:</strong> Built an offline BM25 lexical retrieval engine indexing sovereign military doctrines (Indian Navy Rules of Engagement INBR 8, UNCLOS maritime law, Army Border SOPs) with <strong>&lt;40 ms query response time</strong> and zero external cloud LLM dependencies.</li>
          <li><strong>Automated NATO STANAG 2014 SITREP Compiler:</strong> Implemented the tactical Situation Report compiler, procedurally converting fused multi-domain telemetry (optical, SAR, UGS seismic, AIS) into standardized defense intelligence briefs in <strong>&lt;50 ms (16.7 ms REST runtime)</strong>.</li>
          <li><strong>OODA Decision Cycle Compression:</strong> Slashed operational mission-planning cycle time by <strong>96.5%</strong>—compressing a traditional 24-minute manual ops-room procedure down to under <strong>50 seconds operator-paced</strong> (&lt;0.2s machine execution).</li>
          <li><strong>Resilient DDIL Synchronization:</strong> Integrated a store-and-forward SQLite WAL replication pipeline, ensuring <strong>100% alert delivery</strong> and zero packet loss over jammed, degraded, or intermittent 32 kbps tactical combat radio links.</li>
        </ul>
        <div class="metrics-row">
          <span class="metric-pill"><span class="lbl">Doctrine Index:</span> <span class="val">Local BM25 Lexical</span></span>
          <span class="metric-pill"><span class="lbl">RoE Query Latency:</span> <span class="val">&lt; 40 ms</span></span>
          <span class="metric-pill"><span class="lbl">SITREP Standard:</span> <span class="val">STANAG 2014 (&lt;50 ms)</span></span>
          <span class="metric-pill"><span class="lbl">OODA Reduction:</span> <span class="val">96.51% (24m → 50s)</span></span>
          <span class="metric-pill"><span class="lbl">DDIL Deliverability:</span> <span class="val">100.0% (SQLite WAL)</span></span>
        </div>
      </div>

      <!-- OODA LOOP KILL CHAIN TABLE -->
      <div class="section-title" style="margin-top: 6px;">System Integration Matrix: The C4ISR OODA Loop Kill-Chain</div>
      <table class="dossier-table">
        <thead>
          <tr>
            <th>OODA Stage</th>
            <th>Operational Pillar</th>
            <th>Lead Engineer</th>
            <th>Core Subsystem</th>
            <th>Audited Benchmark</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>1. OBSERVE</strong></td>
            <td>Geospatial Data Tiling</td>
            <td><strong>Gagan Bongale</strong></td>
            <td>SAHI Dynamic 1024px Tiling</td>
            <td class="mono highlight-val">1.62 s / Scene, 0.70m CEP50</td>
          </tr>
          <tr>
            <td><strong>1. OBSERVE</strong></td>
            <td>Optical Satellite AI</td>
            <td><strong>Aditya Bajantri</strong></td>
            <td>YOLO11m + YOLO11n WBF</td>
            <td class="mono highlight-val">17.85 ms, 48.46% mAP@50</td>
          </tr>
          <tr>
            <td><strong>2. ORIENT</strong></td>
            <td>SAR & AIS Fusion</td>
            <td><strong>Utsav Nanapur</strong></td>
            <td>Sentinel-1 2D CA-CFAR + SOG/COG</td>
            <td class="mono highlight-val">79.40% Dark Vessel Capture</td>
          </tr>
          <tr>
            <td><strong>2. ORIENT</strong></td>
            <td>Kinematic Threat Triage</td>
            <td><strong>Misbah Falak</strong></td>
            <td>Kalman + JPDA + Threat Matrix</td>
            <td class="mono highlight-val">0 ID Switches, 86.54% Workload Cut</td>
          </tr>
          <tr>
            <td><strong>3. DECIDE</strong></td>
            <td>Doctrine Advisory & SITREP</td>
            <td><strong>Niyati Gogri</strong></td>
            <td>Sovereign BM25 RAG + STANAG</td>
            <td class="mono highlight-val">&lt;40 ms RoE, &lt;50 ms SITREP</td>
          </tr>
          <tr>
            <td><strong>4. ACT</strong></td>
            <td>Tactical C2 Interface</td>
            <td><strong>Shalina Maniyar</strong></td>
            <td>Zero-Egress React C2 Dashboard</td>
            <td class="mono highlight-val">0 Outbound Calls, Real-time Sync</td>
          </tr>
        </tbody>
      </table>

      <!-- CLOSING STATEMENT -->
      <div class="quote-box">
        <strong>Judges Briefing Conclusion:</strong> "Every member of Team BotS owned an indispensable operational phase of modern digital warfare: from raw orbital sensor ingestion (Gagan) and multi-modal edge AI (Aditya, Utsav), through mathematical kinematics and cognitive auto-triage (Misbah), to sovereign doctrine synthesis (Niyati) and tactical command visualization (Shalina). The result is an integrated, air-gapped defense platform proven under reproducible, rigorous evaluation."
      </div>
    </div>

    <div class="footer">
      <span>Project Rakshak 2.0 // Team BotS Technical Evaluation Dossier</span>
      <span>Page 3 of 3</span>
    </div>
  </div>

</body>
</html>
"""

# Write HTML file
with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"Generated HTML at: {OUTPUT_HTML}")

# Generate PDF with msedge
cmd = [
    str(EDGE_EXE),
    "--headless",
    "--disable-gpu",
    "--no-pdf-header-footer",
    f"--print-to-pdf={OUTPUT_PDF}",
    str(OUTPUT_HTML)
]

print("Executing Microsoft Edge headless PDF compilation...")
res = subprocess.run(cmd, capture_output=True, text=True)
print(f"Exit code: {res.returncode}")

if OUTPUT_PDF.exists():
    reader = PdfReader(str(OUTPUT_PDF))
    total_pages = len(reader.pages)
    print(f"SUCCESS: Generated PDF at {OUTPUT_PDF} ({OUTPUT_PDF.stat().st_size} bytes)")
    print(f"Exact Page Count: {total_pages}")
    for idx, p in enumerate(reader.pages):
        txt = p.extract_text().strip()
        first_line = txt.splitlines()[0] if txt.splitlines() else "EMPTY"
        print(f"  Page {idx+1}: {len(txt)} chars | Starts with: '{first_line[:60]}'")
else:
    print(f"ERROR: Failed to create PDF. Stderr: {res.stderr}")
