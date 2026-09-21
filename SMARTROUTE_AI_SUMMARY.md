# SmartRoute AI — Comprehensive System & Integration Summary

## 1. Project Overview & Mission
**SmartRoute AI** is an AI-powered, multi-agent emergency vehicle routing and decision-support dashboard engineered for **Smart India Hackathon (SIH)**. Unlike standard consumer navigation apps that focus solely on the fastest path, SmartRoute AI evaluates real-time multi-factor risks—including dynamic traffic congestion, heavy rainfall, flood risks, road infrastructure vulnerabilities, and active incident reports—to recommend the safest, most reliable corridor for emergency missions.

The operational focus of this prototype is targeted to the **Hyderabad Metropolitan Area** (16.80°N – 17.90°N, 78.00°E – 79.00°E).

---

## 2. Core Enhancements & Accomplishments

### A. Real Traffic-Aware Routing Architecture (HERE Routing API v8)
- **Provider Abstraction Layer**: Built an extensible abstraction (RoutingProvider ABC) allowing seamless switching between routing engines.
- **HERE Routing API v8**: Integrated as the primary routing provider:
  - Uses 
outingMode=fast to calculate ETAs based on real-time live traffic conditions.
  - Decodes HERE Flexible Polyline geometry using the lexpolyline library.
  - Dynamically calculates traffic delay: Delay = typicalDuration - duration.
  - Classifies traffic into clean indicators: **Low** (<2 min delay), **Moderate** (2–10 min delay), or **Heavy** (>10 min delay).
- **Decoupled Architecture**: Strictly maintains the conceptual separation between **Traffic ETA** (provided by routing APIs) and **SmartRoute Risk Score** (calculated by our custom multi-factor AI risk engine).

### B. Reliable Fallback & Anti-Fabrication Safeguards
- **Geoapify Routing API v1**: Retained as a robust secondary provider. Executes parallel requests for alanced and short corridors to discover distinct physical alternatives.
- **OSRM Engine**: Acts as an unauthenticated tertiary fallback.
- **Strict Anti-Fabrication Rule**: The system never produces fake or synthetic route coordinates on provider failure. If live feeds fail, clean HTTP status codes (502 / 504) and descriptive error messages are returned with an option to load the explicit demo dataset.

### C. Hyderabad Prototype Operational Focus
- **Geofencing & Boundary Validation**: Source and destination coordinates are checked against Hyderabad metropolitan limits (16.80° – 17.90°N, 78.00° – 79.00°E). Non-local queries return a clear, user-friendly HTTP 400 validation error.
- **Map Defaults**: Initialized with center at Hyderabad (17.3850°N, 78.4867°E) at zoom level 11.5, automatically auto-fitting to genuine routes once computed.

### D. Simplified, SIH-Ready Frontend Dashboard
- Streamlined user experience down to the essential 5-step emergency workflow:
  1. Input Source -> 2. Input Destination -> 3. Select Vehicle -> 4. Select Priority -> 5. Analyze Route.
- Added dynamic **Traffic Status Badges** (🟢 Low, 🟡 Moderate, 🔴 Heavy) directly within the Route Comparison table.
- Removed developer-only clutter while preserving full underlying analytical capabilities.

---

## 3. Technologies, Frameworks, & Libraries Used

### Backend Stack
| Technology / Library | Purpose |
| :--- | :--- |
| **Python 3.13** | Core backend runtime |
| **FastAPI** | High-performance asynchronous REST API framework |
| **Pydantic v2** | Strict schema validation, DTOs, and serialization |
| **Uvicorn** | ASGI web server |
| **Requests** | Synchronous HTTP client with connection pooling |
| **flexpolyline** | Decoding HERE Flexible Polyline compressed geometries |
| **Scikit-Learn / Joblib** | Pre-trained ML delay prediction models |
| **python-dotenv** | Secure environment variable management |
| **unittest / TestClient** | Automated integration and regression test suites |

### Frontend Stack
| Technology / Library | Purpose |
| :--- | :--- |
| **React 18** | Component-based UI library |
| **TypeScript** | Static typing and interface enforcement |
| **Vite** | Modern, fast frontend build tool and development server |
| **Leaflet & React-Leaflet** | Interactive geospatial map visualization |
| **CSS3 (Custom Design System)** | High-contrast emergency response theme with glassmorphism |

### External APIs & Data Feeds
| Service | Role in SmartRoute AI |
| :--- | :--- |
| **HERE Routing API v8** | Live traffic-aware driving routes, real-time ETA, and geometry |
| **Geoapify Routing API v1** | Multi-corridor route computation (balanced & short paths) |
| **Geoapify Geocoding API** | Address and landmark resolution to geographic coordinates |
| **OpenStreetMap / Nominatim** | Secondary geocoding fallback |
| **OSRM (Project OSRM)** | Open-source driving route fallback |
| **Open-Meteo API** | Real-time weather, precipitation, and storm condition feeds |

---

## 4. Architectural Data Flow

`
User Query (Source, Destination, Vehicle, Priority)
                    │
                    ▼
[RouteAgent] ── Parallel Geocoding (Geoapify / Nominatim / DB)
                    │
                    ├──► Enforce Hyderabad Metro Bounds Check
                    │
                    ▼
[RoutingService] ── Priority Provider Cascade:
                    ├─ 1. HERE API v8 (Traffic-aware ETA + FlexPolyline)
                    ├─ 2. Geoapify API v1 (Parallel Balanced/Short)
                    └─ 3. OSRM Fallback
                    │
                    ▼
[Parallel Multi-Sensor Agents]
  ├─ TrafficAgent (Live anomaly detection / speed ratio)
  ├─ WeatherAgent (Open-Meteo precipitation & road grip)
  └─ NewsAgent    (Incident reports & geo-tagged events)
                    │
                    ▼
[Risk Engine & ML Predictor]
  ├─ Evaluates multi-factor risk: Traffic (35%), Weather (25%), Incident (25%), Road (15%)
  └─ Predicts congestion-induced travel delays
                    │
                    ▼
[Optimizer Agent & Explainability]
  ├─ Applies vehicle mission profile weights (Ambulance / Truck / Relief)
  ├─ Selects Optimal Recommended Corridor
  └─ Generates clear reasoning & trade-off points
                    │
                    ▼
[Frontend React Dashboard]
  ├─ Leaflet Map: Renders genuine route geometries & incident markers
  ├─ RouteCard: Displays ETA, Distance, Traffic Status, and Risk %
  └─ Explanation Panel: Actionable mission summary
`

---

## 5. Security & Key Management Architecture

1. **Zero Secret Leakage**:
   - API keys are strictly loaded from ackend/.env on the server.
   - Keys are **never** exposed to the React client, JavaScript bundles, or browser network responses.
   - All telemetry and debug logs automatically mask sensitive query parameters (e.g., piKey=HIDDEN).
2. **Clear Error Transparency**:
   - Invalid or unauthorized keys raise explicit PermissionError (500) rather than silently failing.
   - Network timeouts and service unavailability surface clean, actionable error states.

---

## 6. Verification, Testing, & Quality Results

- **Automated Tests**: **50 tests executed** via python -m unittest discover tests (**47 Passed, 3 Skipped** pending HERE live key).
- **TypeScript & Build**: Clean build with **0 errors** across 140 modules (
pm run build).
- **Live Corridor Verification**: Successfully geocoded and generated real routes across Hyderabad corridors (e.g., *Hyderabad City Center -> Secunderabad*, *RGIA -> Secunderabad Station*).

---

## 7. How to Activate HERE Live Traffic

1. Open ackend/.env and supply your HERE API key:
   `env
   HERE_API_KEY=your_here_api_key_here
   `
2. Restart the backend:
   `powershell
   python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
   `
3. Verify live HERE routing:
   `powershell
   python -m unittest tests.test_here_routing -v
   `
