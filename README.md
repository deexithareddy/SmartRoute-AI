# ⚡ SmartRoute AI

### AI-Powered Risk-Aware Emergency Routing & Decision-Support System

**Smart India Hackathon 2025 — Project Documentation**

---

## 📌 1. Project Title
**SmartRoute AI: Emergency Route Intelligence System**

---

## 🎯 2. One-Line Mission
> **SmartRoute AI answers not just *"which route is fastest"* but *"which route gives the best balance of speed, safety, reliability, and disruption risk"* — and it never claims more certainty than its data supports.**

---

## 🚨 3. Problem Statement
Emergency vehicles in Indian metropolitan regions (ambulances, critical medical supply transports, disaster relief convoys) face complex dynamic transit environments:
- **Blind Speed-Only Navigation**: Conventional GPS navigation optimizes solely for shortest distance or nominal travel time without incorporating multi-hazard risk (waterlogging, active structural incidents, severe congestion anomalies).
- **One-Size-Fits-All Routing**: An acute ambulance carrying a trauma patient prioritizes raw transit velocity, whereas a medical supply truck carrying fragile cold-chain vaccines prioritizes road surface smoothness and reliability. Current tools lack vehicle-specific mission optimization.
- **Black-Box Decision Making**: Navigation systems fail to explain *why* a particular diversion was recommended or why an apparently faster arterial was bypassed.
- **Silent Failures & False Confidence**: When telemetry sensors disconnect or fail, consumer navigation tools guess unreliably with full apparent certainty.
- **Lack of Pre-Dispatch Stress Testing**: Emergency response managers cannot simulate "what-if" extreme weather and road-closure contingencies without affecting active operations.

---

## 💡 4. Proposed Solution
SmartRoute AI delivers an end-to-end, multi-agent AI emergency decision-support platform:
1. **Real-World Graph Routing**: Interfaces with OpenStreetMap (OSRM) and Nominatim geocoding to evaluate live physical road corridors.
2. **Multi-Source Telemetry Ingestion**: Concurrently aggregates real-time traffic speeds, Open-Meteo meteorological parameters (rainfall, visibility, wind gusts), and CAD municipal incident alerts.
3. **Multi-Factor Composite Risk Modeling**: Evaluates dynamic risk across 4 weighted vectors: Traffic (35%), Weather (25%), Incidents (25%), and Road Class (15%).
4. **Hybrid Transit Delay Regression**: Machine learning transit delay prediction with deterministic rule-based fallback when sensor feeds are degraded.
5. **Configurable Mission Profile Optimization**: Multi-criteria utility scoring dynamically tailored for Ambulances, Medical Supply Trucks, and Disaster Relief Convoys.
6. **Zero-Hallucination Explainability Engine**: Generates mathematically grounded rationale for selected and rejected candidate corridors.
7. **Isolated What-If Scenario Sandbox**: Allows operators to stress-test extreme precipitation and road closures without mutating live operational telemetry.
8. **Jury-Optimized Presentation Mode & Guided Tour**: Dedicated 12-step guided demonstration and high-readability presentation HUD for evaluator review.

---

## 🏆 5. Key Innovations

| Innovation | Implementation & Impact |
| :--- | :--- |
| **Strict Cause Honesty** | Traffic speed drops are labeled `Cause: UNKNOWN` unless independently verified by CAD incident alerts on that exact corridor. Zero hallucinated collision explanations. |
| **Transparent 4-Factor Risk Engine** | Mathematical formula ($0.35T + 0.25W + 0.25I + 0.15R$) with configurable weights validated to sum to 1.0 at boot. |
| **Hybrid ML / Rule-Based Fallback** | Suppresses ML inference when telemetry feeds are incomplete; transitions to transparent rule-based heuristics with clear UI disclosure. |
| **Honest Confidence Degradation** | Data confidence degrades in 4 discrete tiers ($95\% ightarrow 75\% ightarrow 50\% ightarrow 25\%$) proportional to active sensor coverage. |
| **Vehicle-Specific Optimization Profiles** | Dynamic trade-off re-weighting ($W_t, W_r, W_d, W_l$) that re-ranks routes based on whether the payload is acute trauma care or cold-chain logistics. |
| **Single-Corridor Honesty Guard** | When only one physical path exists, the system warns the dispatcher rather than synthesizing dummy candidate routes. |
| **Isolated What-If Sandbox** | Performs in-memory deep-copy stress testing without altering background live operational feeds. |
| **SIH Jury Presentation Mode** | Full-screen 2-column view surfacing recommendation hero cards, risk bars, and a 6-step decision flowchart readable in 10 seconds. |
| **12-Step Guided Presenter Tour** | Automated presenter tour cycling through emergency scenarios with real-time HUD metrics and presenter cues. |

---

## 👥 6. Target Users

| User Group | Operational Role | Primary Benefit |
| :--- | :--- | :--- |
| **Emergency Dispatch Operators (108 / 112)** | Ambulance & First Responder Routing | Real-time risk mitigation and fastest safe corridor selection |
| **Hospital Logistics & Supply Managers** | Organ & Cold-Chain Vaccine Transport | Low-vibration, high-reliability route planning |
| **Disaster Management Authorities (NDRF / SDMA)** | Flood & Disaster Relief Convoy Dispatch | Clearance-aware routing avoiding inundated subways and closures |
| **Municipal Traffic Command Centers** | Traffic Ingestion & Incident Correlation | Verified multi-corridor situational awareness |
| **Hackathon Evaluators / SIH Jury** | Solution Assessment | Fast verification via Presentation Mode and Guided Tour |

---

## 🏗️ 7. System Architecture

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                            REACT FRONTEND (Vite)                            │
│  RouteInput · Leaflet Map · RouteCard · RiskPanel · ExplanationPanel        │
│  DataStatus · SimulationPanel · DemoModeBar · FullDemoTour · PresentationMode│
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTP REST (JSON)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          FASTAPI BACKEND (main.py)                          │
│                                                                             │
│  ┌─── MULTI-AGENT ORCHESTRATION PIPELINE ───────────────────────────────┐   │
│  │                                                                      │   │
│  │   [RouteAgent]                                                       │   │
│  │       │ OSRM candidate route generation & Nominatim geocoding        │   │
│  │       ▼                                                              │   │
│  │   [TrafficAgent] ───── [WeatherAgent] ───── [NewsAgent]              │   │
│  │   (Concurrent Execution via ThreadPoolExecutor)                      │   │
│  │       │                        │                    │                │   │
│  │       └─────────────────────── ▼ ───────────────────┘                │   │
│  │                          [RiskEngine]                                │   │
│  │               0.35·T + 0.25·W + 0.25·I + 0.15·R                      │   │
│  │                               │                                      │   │
│  │                          [Predictor]                                 │   │
│  │               ML (GradientBoosting) → Rule Fallback                  │   │
│  │                               │                                      │   │
│  │                       [OptimizerAgent]                               │   │
│  │               Mission Profile multi-criteria scoring                 │   │
│  │                               │                                      │   │
│  │                    [ExplainabilityEngine]                            │   │
│  │               Grounded mathematical decision rationale               │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─ Core Services & Security Layer ──────────────────────────────────────┐  │
│  │  DemoService (7 SIH Scenarios) · TelemetryLogger · SimulationAgent   │  │
│  │  SecurityConfig (CORS, Size Limit 1MB, Fault-Inject Gating)           │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
            ┌──────────────────────────┼──────────────────────────┐
            ▼                          ▼                          ▼
      [OSRM Engine]            [Open-Meteo API]          [CAD Incident Stream]
    (Road Network Graph)       (Live Weather Radar)      (Emergency Feeds)
```

---

## 💻 8. Technology Stack

### Backend Technologies
- **Language & Runtime**: Python 3.10+ / 3.13
- **Web Framework**: FastAPI 0.115 (ASGI async web framework)
- **ASGI Server**: Uvicorn
- **Machine Learning**: scikit-learn 1.4 (`GradientBoostingRegressor`), joblib, numpy
- **Data Validation**: Pydantic v2 schemas
- **Concurrency**: `concurrent.futures.ThreadPoolExecutor` for parallel multi-agent telemetry fetching
- **Testing**: pytest & AnyIO test suite

### Frontend Technologies
- **Framework**: React 18 with TypeScript 5
- **Build Tool**: Vite 5
- **Mapping & GIS**: Leaflet.js, React-Leaflet
- **Styles**: Custom CSS3 Dark-Theme Mission Control System (~3,100 lines)

### External Telemetry Services (Open & Accessible)
- **OSRM (Project-OSRM)**: OpenStreetMap routing engine
- **Nominatim**: OSM Geocoding
- **Open-Meteo**: High-resolution meteorological data API
- **CAD Stream**: Police & municipal incident feed

---

## 📁 9. Project Structure

```text
SmartRoute AI/
├── backend/
│   ├── main.py                     # FastAPI routes, pipeline orchestrator, security
│   ├── config.py                   # Security settings, CORS, payload limits
│   ├── agents/
│   │   ├── route_agent.py          # OSRM path generation
│   │   ├── traffic_agent.py        # Speed ratio anomaly detection
│   │   ├── weather_agent.py        # Segment weather risk scoring
│   │   ├── news_agent.py           # Spatial CAD incident matching
│   │   ├── optimizer_agent.py      # Mission profile optimization
│   │   └── simulation_agent.py     # What-if scenario stress engine
│   ├── engine/
│   │   ├── risk_engine.py          # 4-factor composite risk formula
│   │   ├── scoring.py              # Mission profile weighted scoring
│   │   └── explainability.py       # Grounded mathematical rationale
│   ├── ml/
│   │   ├── model.py                # GradientBoostingRegressor, training, audit metadata
│   │   ├── predictor.py            # Hybrid ML / rule-based inference
│   │   └── delay_model.joblib      # Trained model weights
│   ├── services/
│   │   ├── routing_service.py      # OSRM & Nominatim client
│   │   ├── traffic_service.py      # Traffic speed client
│   │   ├── weather_service.py      # Open-Meteo API client
│   │   ├── news_service.py         # CAD incident client
│   │   ├── demo_service.py         # 7 SIH demo scenarios
│   │   └── telemetry_logger.py     # Pipeline timing audit logger
│   ├── models/
│   │   └── schemas.py              # Pydantic data schemas
│   └── data/
│       └── sample_data.json        # Curated incidents & synthetic data
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Map/                # Leaflet map with polylines & incident markers
│   │   │   ├── RouteCard/          # Route comparison table & dynamic labels
│   │   │   ├── RiskPanel/          # AI recommendation & risk breakdown
│   │   │   ├── ExplanationPanel/   # XAI comparative & corridor tabs + ML audit
│   │   │   ├── DataStatus/         # Feed status & freshness badges
│   │   │   ├── SimulationPanel/    # What-if sandbox controls
│   │   │   ├── RouteInput/         # Emergency dispatch input parameters
│   │   │   ├── DemoModeBar/        # SIH scenario chips & Run Full Demo launcher
│   │   │   ├── FullDemoTour/       # 12-step presenter tour modal with HUD metrics
│   │   │   └── PresentationMode/   # 2-column jury presentation layout
│   │   ├── pages/
│   │   │   └── Dashboard.tsx       # Root operations dashboard
│   │   ├── services/
│   │   │   └── api.ts              # Typed API service
│   │   ├── types/
│   │   │   └── route.ts            # TypeScript interfaces
│   │   └── App.css                 # Mission control dark theme stylesheet
├── tests/
│   └── test_pipeline_e2e.py        # 20 end-to-end pytest cases
├── .env.example                    # Environment variable template
├── requirements.txt                # Python dependencies
└── README.md                       # Complete SIH project documentation
```

---

## ⚙️ 10. Setup Instructions

### 1. Prerequisites
- Python 3.10+ (Tested on Python 3.13)
- Node.js 18+ and npm 9+

### 2. Backend Setup
```bash
# In the project root directory
python -m venv .venv

# On Windows:
.venv\Scriptsctivate
# On Linux/macOS:
source .venv/bin/activate

# Install Python requirements
pip install -r requirements.txt

# Start backend server
python -m uvicorn backend.main:app --port 8000 --reload
```
Backend API will be live at: `http://127.0.0.1:8000`  
Interactive Docs: `http://127.0.0.1:8000/docs`

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Frontend will be live at: `http://localhost:5173`

---

## 🔐 11. Environment Variables

Create a `.env` file in the root based on `.env.example`:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `ENVIRONMENT` | `development` | Runtime mode (`development`, `staging`, `production`) |
| `DEBUG` | `false` | Server debug mode (false in production to prevent stack trace leaks) |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Allowed CORS origins for dashboard API access |
| `MAX_REQUEST_SIZE_BYTES` | `1048576` | Maximum request body limit (1 MB) |
| `DATABASE_URL` | `sqlite:///./smartroute.db` | Local SQLite or Production PostgreSQL connection URL |
| `OSRM_BASE_URL` | `http://router.project-osrm.org` | OpenStreetMap routing endpoint |
| `NOMINATIM_BASE_URL` | `https://nominatim.openstreetmap.org` | OpenStreetMap geocoding endpoint |
| `ALLOW_DEV_FAULT_INJECTION` | `true` | Enables fault-injection in dev (Blocked in production) |

---

## 📡 12. API Documentation

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Core health check status |
| `GET` | `/api/data-status` | Telemetry feed status, freshness, and confidence |
| `POST` | `/api/analyze` | Main route analysis, multi-factor risk, ML delay, and optimization |
| `POST` | `/api/simulate` | Isolated what-if scenario simulation sandbox |
| `GET` | `/api/optimization-profiles` | Mission profile weight configurations |
| `POST` | `/api/optimization-profiles/configure` | Runtime configuration of mission profile weights |
| `GET` | `/api/ml/metadata` | Machine learning model metadata and synthetic data audit |
| `GET` | `/api/demo/scenarios` | List of 7 standardized SIH demo scenarios |
| `POST` | `/api/demo/activate` | Activate a deterministic SIH demo scenario |
| `POST` | `/api/demo/reset` | Reset demo state and restore live pipeline |
| `POST` | `/api/fault-inject` | Dev-only telemetry fault injection |
| `GET` | `/api/telemetry-logs` | Backend timing logs for pipeline stages |

---

## 🧮 13. Risk Calculation Methodology

### Multi-Factor Composite Risk Index
$$	ext{Overall Risk} = 0.35 	imes 	ext{Traffic} + 0.25 	imes 	ext{Weather} + 0.25 	imes 	ext{Incident} + 0.15 	imes 	ext{Road}$$

- **Traffic Risk (35%)**: Computed from speed ratio anomaly: $\max(0, 1.0 - 	ext{speed\_ratio})$.
- **Weather Risk (25%)**: Evaluated across rainfall rate, wind velocity, and visibility along polyline waypoints.
- **Incident Risk (25%)**: Computed via spatial proximity to CAD emergency incidents.
- **Road Risk (15%)**: Highway/Expressway (0.10) vs Primary Arterial (0.25) vs Secondary (0.45).

### Risk Classification Bands
- `0.00 - 0.25` : **LOW** (Emerald Green)
- `0.25 - 0.50` : **MODERATE** (Amber Yellow)
- `0.50 - 0.75` : **HIGH** (Orange)
- `0.75 - 1.00` : **SEVERE / CRITICAL** (Crimson Red)

---

## 🤖 14. ML Methodology & Limitations

### Delay Prediction Architecture
- **Model**: `GradientBoostingRegressor (scikit-learn)` (`n_estimators=120, learning_rate=0.08, max_depth=4`)
- **12 Features**: observed_speed, expected_speed, speed_ratio, baseline_duration_minutes, rainfall_mm, visibility_m, wind_speed_kmh, incident_count, incident_severity, road_type_code, hour_of_day, day_of_week.
- **Training Data**: 1,600 synthetic simulated journey records.
- **Validation Holdout**: 400 synthetic records ($	ext{MAE} pprox 0.82	ext{ min}$, $R^2 pprox 0.941$).

> [!CAUTION]
> **Synthetic Data Disclosure**: The ML model was trained on a physics-grounded synthetic simulation corpus. Evaluation metrics reflect synthetic test holdouts, **NOT real-world production fleet validation**. The system transparently falls back to deterministic rule-based heuristics if telemetry is incomplete.

---

## 🤝 15. Multi-Agent Architecture

```text
1. RouteAgent       → Fetches candidate paths from OSRM
2. Concurrent Pull  → TrafficAgent (speeds), WeatherAgent (rain/wind), NewsAgent (CAD alerts)
3. RiskEngine       → Computes 4-factor composite risk
4. Predictor        → ML delay estimation (or rule-based fallback)
5. OptimizerAgent   → Vehicle-specific mission profile scoring:
                      Route Score = W_t·ETA + W_r·Risk + W_d·Delay + W_l·(1-Reliability)
6. Explainability   → Generates grounded mathematical explanation bullets
```

---

## 🧪 16. Scenario Simulation & SIH Demo Scenarios

The 7 standardized SIH demonstration scenarios:
1. **Normal Conditions**: Clear weather, free-flow traffic $ightarrow$ Route A recommended (16m ETA, 14% risk).
2. **Severe Traffic Anomaly**: Sudden speed drop on Route A (12 km/h, Cause: UNKNOWN) $ightarrow$ Route B recommended.
3. **Heavy Rainfall (45 mm/h)**: Surface road flooding risk $ightarrow$ Elevated Route B expressway recommended.
4. **Confirmed CAD Incident**: Police-reported collision on Route A $ightarrow$ Incident marker & Route B recommended.
5. **Road Closure**: Arterial impassable $ightarrow$ Route A labeled CLOSED; Route B selected.
6. **Traffic Data Unavailable**: Speed sensor cut $ightarrow$ 75% MODERATE confidence & Rule-Based Fallback.
7. **Only One Route Available**: Single corridor $ightarrow$ Honesty warning banner without synthetic routes.

---

## 🛡️ 17. Data Confidence & Freshness Model

### Confidence Tiers
- **4/4 Feeds Live**: HIGH (95% certainty)
- **3/4 Feeds Live**: MODERATE (75% certainty)
- **2/4 Feeds Live**: LOW (50% certainty)
- **≤1/4 Feeds Live**: VERY LOW (25% certainty)

### Freshness Classification
- **FRESH**: Updated < 5 minutes ago (🟢 LIVE)
- **RECENT**: Updated 5–15 minutes ago (🟡 RECENT)
- **STALE**: Updated > 15 minutes ago (🟠 STALE)
- **UNAVAILABLE**: Feed disconnected (⛔ UNAVAILABLE)

---

## ⚖️ 18. Honest-AI Design Principles
1. **No Hallucinated Causes**: Speed collapse labeled `Cause: UNKNOWN` without CAD incident proof.
2. **No False Confidence**: Missing sensors immediately degrade confidence badges.
3. **No Phantom Routes**: Single corridor warnings instead of fabricated alternatives.
4. **Grounded Explanations**: Every reason cites measured numbers (e.g. "4 minutes faster", "57% lower traffic risk").
5. **ML Honesty**: Synthetic training origin clearly disclosed in docs and UI.

---

## ⚠️ 19. Known Limitations (Prototype vs. Production)

| Feature | Prototype Capability (Current) | Production Capability (Future) |
| :--- | :--- | :--- |
| **ML Training Data** | Synthetic physics-modeled dataset | Real municipal AVL / GPS probe traces |
| **Routing Engine** | Public OSRM server instance | Dedicated self-hosted OSRM with local city tiles |
| **Geocoding** | Public Nominatim API (1 req/s limit) | Enterprise licensed GIS geocoding service |
| **Incident Ingestion** | Curated CAD incident feed | Real-time MQTT/WebSocket CAD 911 integration |
| **Telemetry Persistence**| In-memory telemetry logs | PostgreSQL + TimescaleDB time-series database |

---

## 🎬 20. Demo Instructions

### Recommended Jury Presentation:
1. Open the dashboard at `http://localhost:5173`.
2. Click **`📊 Presentation Mode`** in the top navigation header for the clean 2-column jury view.
3. Click **`🎬 Run Full Demo`** to start the 12-step guided presenter tour with auto-advance and 5-metric HUD card.
4. Test interactive what-if simulation sandbox or trigger SIH scenarios 1 through 7 from the top bar.

---

## 🚀 21. Future Scope
- **Real Fleet GPS Calibration**: Fine-tuning ML weights on empirical emergency vehicle AVL traces.
- **WebSocket Streaming**: Sub-second live vehicle telemetry and route reranking.
- **Drone & Air-Ambulance 3D Corridors**: Altitude and airspace risk modeling.
- **Multi-City Support**: Automated OSM tile caching for all Indian Tier-1 & Tier-2 cities.

---

## 🧪 22. Testing Instructions

Run the 20-test automated end-to-end backend test suite:
```bash
python -m pytest tests/ -v
```
*Expected Output: `20 passed in ~4.5s`*

Verify frontend TypeScript types and production build:
```bash
cd frontend
npx tsc --noEmit
npx vite build
```

---

## 📄 23. License
This project is licensed under the **MIT License**.
