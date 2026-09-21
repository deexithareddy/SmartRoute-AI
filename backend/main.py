"""
SmartRoute AI - FastAPI Backend Application

Exposes endpoints for emergency route risk analysis, scenario simulation,
telemetry feed health, dev fault-injection, and service health checks.

Full Orchestration Pipeline:
  RouteAgent -> [TrafficAgent, WeatherAgent, NewsAgent] -> RiskEngine -> Predictor (ML/Fallback) -> OptimizerAgent -> ExplainabilityEngine
"""

import concurrent.futures
import datetime
import logging
import time
from typing import Dict, List, Optional, Tuple
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from backend.config import (
    ENVIRONMENT,
    DEBUG,
    CORS_ORIGINS,
    MAX_REQUEST_SIZE_BYTES,
    SecurityConfig,
    GEOAPIFY_API_KEY,
)
from backend.models.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    SimulateRequest,
    SimulateResponse,
    DataStatusResponse,
    FeedTelemetryStatus,
    TelemetryLogsResponse,
    TelemetryLogDTO,
    HealthResponse,
    RootStatusResponse,
    TrafficScenarioRequest,
    TrafficScenarioResponse,
    FaultInjectRequest,
    FaultInjectResponse,
    RouteResult,
    RiskFactors,
    IncidentDTO,
    MissionProfileDTO,
    ConfigureProfileRequest,
    MLModelMetadataResponse,
    DemoScenarioListResponse,
    DemoActivateRequest,
    DemoActivateResponse,
)
from backend.ml.model import get_model_metadata
from backend.services.demo_service import demo_service
from backend.services.telemetry_logger import telemetry_logger
from backend.agents.route_agent import route_agent
from backend.agents.weather_agent import weather_agent
from backend.agents.traffic_agent import traffic_agent
from backend.agents.news_agent import news_agent
from backend.agents.optimizer_agent import optimizer_agent
from backend.agents.simulation_agent import simulation_agent
from backend.services.traffic_service import traffic_service
from backend.services.weather_service import weather_service
from backend.services.news_service import news_service
from backend.services.routing_service import routing_service
from backend.engine.risk_engine import risk_engine
from backend.engine.scoring import scoring_engine
from backend.engine.explainability import explainability_engine

# Configure secure server logger
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("SmartRouteAI")

app = FastAPI(
    title="SmartRoute AI API",
    description="AI-powered, risk-aware emergency routing and decision-support system",
    version="0.1.0",
    docs_url="/docs" if not SecurityConfig.is_production() else None,
    redoc_url="/redoc" if not SecurityConfig.is_production() else None,
)

# 1. Request Size Limiting Middleware
class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Protects against Denial-of-Service memory exhaustion via oversized payloads."""
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > MAX_REQUEST_SIZE_BYTES:
                    logger.warning(
                        "Payload too large rejected: %s bytes from %s",
                        content_length,
                        request.client.host if request.client else "unknown",
                    )
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={"detail": f"Request payload exceeds maximum allowed limit of {MAX_REQUEST_SIZE_BYTES} bytes."},
                    )
            except ValueError:
                pass
        return await call_next(request)

app.add_middleware(RequestSizeLimitMiddleware)

# 2. Configurable CORS Security Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 3. Global Exception Handlers (Prevents Internal Stack Trace & Error Message Leakage)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Returns clean validation errors without exposing internal server paths."""
    logger.warning("Input validation error on %s: %s", request.url.path, exc.errors())
    clean_errors = [
        {"field": " -> ".join(str(loc) for loc in err["loc"] if loc != "body"), "message": err["msg"]}
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Input validation failed. Please verify parameter constraints.", "errors": clean_errors},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Passes through handled HTTP exceptions with clean messages."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Catches unhandled runtime exceptions, logs full stack trace, and returns safe sanitized response."""
    logger.error("Unhandled runtime exception on %s: %s", request.url.path, str(exc), exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred while processing your request. Please try again or contact emergency dispatch support.",
            "error_id": datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S"),
        },
    )


# ==============================================================================
# Pipeline Orchestrator with Isolated Error Handling & Graceful Degradation
# ==============================================================================

def run_orchestrated_pipeline(
    source: str,
    destination: str,
    vehicle_type: str = "Ambulance",
    priority: str = "Critical",
) -> Tuple[List[RouteResult], Optional[RouteResult], Dict[str, bool], List[str], bool, Tuple[float, float], Tuple[float, float], List[IncidentDTO], Dict[str, float]]:
    """
    Executes the complete multi-agent pipeline with parallel corridor ingestion,
    caching, error isolation, and detailed stage latency instrumentation:
      1. RouteAgent (Parallel Geocoding & OSRM Routing)
      2. Parallel Corridor Sensor Ingestion [WeatherAgent, TrafficAgent, NewsAgent]
      3. RiskEngine (Composite risk calculation)
      4. Predictor & OptimizerAgent (ML delay regression & vehicle mission ranking)
      5. ExplainabilityEngine (Data-grounded dual-perspective rationale)
    """
    pipeline_t0 = time.perf_counter()
    timings: Dict[str, float] = {}

    # --------------------------------------------------------------------------
    # 1. Route Agent: Candidate Path Generation (Parallel Geocoding & Geoapify)
    # --------------------------------------------------------------------------
    t_route_start = time.perf_counter()
    maps_live = routing_service.is_healthy()
    if not maps_live:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Routing and maps feed is unavailable (offline or fault-injected).",
        )

    try:
        routes, alternatives_avail, origin_coords, dest_coords = route_agent.get_candidate_routes(
            source=source,
            destination=destination,
        )
    except ValueError as ve:
        logger.warning("[Orchestrator] Geocoding / input error: %s", ve)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except PermissionError as pe:
        logger.error("[Orchestrator] Configuration error: %s", pe)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Routing service configuration error.",
        )
    except TimeoutError as te:
        logger.error("[Orchestrator] Timeout error: %s", te)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Routing request timed out.",
        )
    except ConnectionError as ce:
        logger.error("[Orchestrator] Connection error: %s", ce)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Live routing service unavailable.",
        )
    except Exception as e:
        logger.error("[Orchestrator] RouteAgent routing error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to generate candidate routes: {str(e)}",
        )

    t_route_end = time.perf_counter()
    timings["routing_geocoding_ms"] = round((t_route_end - t_route_start) * 1000.0, 2)

    # Live service health checks
    traffic_feed_live = traffic_service.is_healthy()
    weather_feed_live = weather_service.is_healthy()
    news_feed_live = news_service.is_healthy()

    # --------------------------------------------------------------------------
    # 2. Parallel Sensor Ingestion across all Candidate Corridors
    # --------------------------------------------------------------------------
    t_sensor_start = time.perf_counter()
    all_incidents_map: Dict[str, IncidentDTO] = {}

    def _evaluate_corridor(route: RouteResult) -> Tuple[RouteResult, Dict[str, bool]]:
        """Worker function to evaluate all sensor agents on a single corridor."""
        # (a) Weather Agent
        try:
            if not weather_feed_live:
                raise ConnectionError("Weather feed unavailable.")
            weather_eval = weather_agent.evaluate_route_weather(route.coordinates)
            w_live = weather_eval.data_available
            w_risk = weather_eval.risk_score if (w_live and weather_eval.risk_score is not None) else 0.20
            w_exp = weather_eval.explanation
        except Exception as err:
            logger.debug("Weather evaluation error on %s: %s", route.code, err)
            w_live = False
            w_risk = 0.20
            w_exp = "⚠️ Weather telemetry offline — using baseline weather risk"

        # (b) Traffic Agent
        try:
            if not traffic_feed_live:
                raise ConnectionError("Traffic feed unavailable.")
            traffic_eval = traffic_agent.evaluate_route_traffic(
                coordinates=route.coordinates,
                road_name=route.name,
            )
            t_live = traffic_eval.data_available
            t_risk = traffic_eval.risk_score if (t_live and traffic_eval.risk_score is not None) else 0.30
            t_exp = traffic_eval.explanation
            has_anomaly = traffic_eval.has_anomaly
            obs_speed = traffic_eval.observed_speed_kmh
            exp_speed = traffic_eval.expected_speed_kmh
        except Exception as err:
            logger.debug("Traffic evaluation error on %s: %s", route.code, err)
            t_live = False
            t_risk = 0.30
            t_exp = "⚠️ Traffic telemetry offline — using baseline flow risk"
            has_anomaly = False
            obs_speed = None
            exp_speed = 45.0
            traffic_eval = None

        # (c) News / Incident Agent
        try:
            if not news_feed_live:
                raise ConnectionError("News feed unavailable.")
            news_eval = news_agent.evaluate_route_incidents(route.coordinates)
            n_live = news_eval.data_available
            inc_risk = news_eval.incident_risk_score if (n_live and news_eval.incident_risk_score is not None) else 0.0
            has_inc = news_eval.has_incidents
            matched_inc = news_eval.matched_incidents
        except Exception as err:
            logger.debug("News evaluation error on %s: %s", route.code, err)
            n_live = False
            inc_risk = 0.0
            has_inc = False
            matched_inc = []

        # Resolve Traffic Anomaly cause if active incident confirmed on same corridor
        if has_anomaly and has_inc and matched_inc:
            primary_inc = matched_inc[0]
            t_exp = (
                f"⚠️ Traffic anomaly confirmed by incident feed: {primary_inc.headline} "
                f"(Observed speed {obs_speed:.1f} km/h vs expected {exp_speed:.1f} km/h)"
            )

        # Composite Risk Computation
        road_risk = risk_engine.estimate_road_risk(route.name)
        overall_risk = risk_engine.compute_overall_risk(
            traffic_risk=t_risk,
            weather_risk=w_risk,
            incident_risk=inc_risk,
            road_risk=road_risk,
        )

        feed_avail_corridor = {
            "traffic": t_live,
            "weather": w_live,
            "news": n_live,
            "maps": maps_live,
        }
        conf_lbl, conf_pct, _ = risk_engine.calculate_confidence(feed_avail_corridor)
        risk_band_label = risk_engine.map_risk_to_label(overall_risk)
        risk_percent = int(round(overall_risk * 100))

        route.risk_percent = risk_percent
        route.status = risk_band_label
        route.confidence_score = conf_pct
        route.risk_factors = RiskFactors(
            traffic=t_risk,
            weather=w_risk,
            incident=inc_risk,
            road=road_risk,
            overall_risk=overall_risk,
        )

        # Traffic Anomaly details for Map Visualization
        if has_anomaly and route.coordinates and traffic_eval:
            midpoint_idx = len(route.coordinates) // 2
            route.traffic_anomaly = {
                "has_anomaly": True,
                "severity": traffic_eval.anomaly_severity if hasattr(traffic_eval, "anomaly_severity") else "SEVERE",
                "observed_speed": obs_speed,
                "expected_speed": exp_speed,
                "speed_ratio": traffic_eval.speed_ratio if hasattr(traffic_eval, "speed_ratio") else 0.35,
                "cause": traffic_eval.cause if hasattr(traffic_eval, "cause") else "UNKNOWN",
                "explanation": t_exp,
                "coordinate": route.coordinates[midpoint_idx],
            }
        else:
            route.traffic_anomaly = None

        # Incidents for Map Visualization
        route.incidents = []
        if has_inc and matched_inc:
            for inc in matched_inc:
                inc_lat = inc.lat if inc.lat != 0.0 else (route.coordinates[len(route.coordinates) // 3][0] if route.coordinates else 12.9716)
                inc_lng = inc.lng if inc.lng != 0.0 else (route.coordinates[len(route.coordinates) // 3][1] if route.coordinates else 77.5946)
                inc_dto = IncidentDTO(
                    incident_id=inc.incident_id,
                    headline=inc.headline,
                    event_type=inc.event_type,
                    severity=inc.severity,
                    location_name=inc.location_name,
                    lat=inc_lat,
                    lng=inc_lng,
                    reported_time=inc.reported_time,
                    affected_route_ids=[route.id],
                )
                route.incidents.append(inc_dto)

        # Check Road Passability
        is_closed = "closed" in route.name.lower() or "impassable" in route.name.lower()
        route.is_passable = not is_closed

        route.explanation_points = []
        if n_live:
            if has_inc:
                for inc in matched_inc:
                    route.explanation_points.append(
                        f"⚠️ Active Incident: {inc.headline} (Severity: {inc.severity.upper()}, {inc.min_distance_km}km from corridor)"
                    )
            else:
                route.explanation_points.append(
                    "✓ No reported incidents, closures, or emergency lane blockages"
                )
        else:
            route.explanation_points.append(
                "⚠️ Incident telemetry offline — route disruption status unverified"
            )

        route.explanation_points.append(t_exp)
        route.explanation_points.append(w_exp)
        route.explanation_points.append(
            f"📊 Composite Risk: {risk_percent}% ({risk_band_label}) [Traffic: {t_risk*100:.0f}%, Weather: {w_risk*100:.0f}%, Incident: {inc_risk*100:.0f}%, Road: {road_risk*100:.0f}%]"
        )

        return route, feed_avail_corridor

    # Execute corridor sensor ingestion in parallel threads
    evaluated_routes: List[RouteResult] = []
    feed_states_list: List[Dict[str, bool]] = []

    if routes:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, len(routes))) as executor:
            future_results = [executor.submit(_evaluate_corridor, r) for r in routes]
            for future in future_results:
                try:
                    res_route, res_feeds = future.result()
                    evaluated_routes.append(res_route)
                    feed_states_list.append(res_feeds)
                    for inc in res_route.incidents:
                        if inc.incident_id not in all_incidents_map:
                            all_incidents_map[inc.incident_id] = inc
                        else:
                            if res_route.id not in all_incidents_map[inc.incident_id].affected_route_ids:
                                all_incidents_map[inc.incident_id].affected_route_ids.append(res_route.id)
                except Exception as err:
                    logger.error("Corridor worker thread exception: %s", err)

    t_sensor_end = time.perf_counter()
    timings["sensor_ingestion_ms"] = round((t_sensor_end - t_sensor_start) * 1000.0, 2)

    # --------------------------------------------------------------------------
    # 3. Predictor & Optimizer Agent: Mission Optimization
    # --------------------------------------------------------------------------
    t_opt_start = time.perf_counter()
    overall_feeds = {
        "traffic": traffic_feed_live,
        "weather": weather_feed_live,
        "news": news_feed_live,
        "maps": maps_live,
    }

    try:
        ranked_routes, recommended_route = optimizer_agent.optimize_routes(
            routes=evaluated_routes,
            vehicle_type=vehicle_type,
            priority=priority,
            traffic_telemetry_available=traffic_feed_live,
            weather_telemetry_available=weather_feed_live,
        )
    except Exception as e:
        logger.warning("[Orchestrator] OptimizerAgent error: %s. Using baseline ordering.", e)
        ranked_routes = evaluated_routes
        recommended_route = evaluated_routes[0] if evaluated_routes else None

    t_opt_end = time.perf_counter()
    timings["ml_optimizer_ms"] = round((t_opt_end - t_opt_start) * 1000.0, 2)

    # --------------------------------------------------------------------------
    # 4. Explainability Engine: Grounded Natural Language Narrative
    # --------------------------------------------------------------------------
    t_exp_start = time.perf_counter()
    try:
        explanation_bullets = explainability_engine.generate_recommendation_explanation(
            recommended_route=recommended_route,
            all_routes=ranked_routes,
            feed_availability=overall_feeds,
            vehicle_type=vehicle_type,
            priority=priority,
        )
    except Exception as e:
        logger.warning("[Orchestrator] ExplainabilityEngine error: %s", e)
        explanation_bullets = [
            f"{recommended_route.code if recommended_route else 'Primary route'} recommended based on multi-factor risk assessment."
        ]
    t_exp_end = time.perf_counter()
    timings["explainability_ms"] = round((t_exp_end - t_exp_start) * 1000.0, 2)

    total_latency_ms = (time.perf_counter() - pipeline_t0) * 1000.0
    timings["total_analyze_ms"] = round(total_latency_ms, 2)

    logger.info(
        "[Pipeline Latency] Total: %.2fms | Routing/Geocoding: %.2fms | Sensor Ingestion: %.2fms | ML/Optimizer: %.2fms | Explainability: %.2fms",
        total_latency_ms,
        timings["routing_geocoding_ms"],
        timings["sensor_ingestion_ms"],
        timings["ml_optimizer_ms"],
        timings["explainability_ms"],
    )

    return (
        ranked_routes,
        recommended_route,
        overall_feeds,
        explanation_bullets,
        alternatives_avail,
        origin_coords,
        dest_coords,
        list(all_incidents_map.values()),
        timings,
    )


# ==============================================================================
# Endpoints
# ==============================================================================

@app.get("/", response_model=RootStatusResponse)
def get_root() -> RootStatusResponse:
    """Root service status and API discovery endpoint."""
    return RootStatusResponse(
        service="SmartRoute AI",
        status="running",
        description="FastAPI Multi-Agent Orchestration Service",
        docs="/docs",
        health="/api/health",
    )


@app.get("/health", response_model=HealthResponse)
@app.get("/api/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Service health check endpoint."""
    return HealthResponse(status="ok")


@app.get("/api/data-status", response_model=DataStatusResponse)
def get_data_status() -> DataStatusResponse:
    """Returns real-time status and reliability of external telemetry feeds."""
    traffic_healthy = traffic_service.is_healthy()
    weather_healthy = weather_service.is_healthy()
    news_healthy = news_service.is_healthy()
    maps_healthy = routing_service.is_healthy()

    traffic_log = telemetry_logger.get_latest_state("Traffic Grid & Speed Sensors")
    weather_log = telemetry_logger.get_latest_state("Open-Meteo Atmospheric Telemetry")
    news_log = telemetry_logger.get_latest_state("CAD Incidents & Municipal Alerts")
    maps_log = (
        telemetry_logger.get_latest_state("Geoapify Routing")
        or telemetry_logger.get_latest_state("Geoapify Geocoding")
        or telemetry_logger.get_latest_state("OSRM Highway Routing")
        or telemetry_logger.get_latest_state("Nominatim Geocoding")
    )

    traffic_provider_type = traffic_service.get_active_provider_type()
    traffic_scenario = traffic_service.get_scenario_mode()

    def get_prov(is_h: bool, log_entry, default_prov="LIVE") -> str:
        if not is_h:
            return "UNAVAILABLE"
        if log_entry:
            return log_entry.provenance
        return default_prov

    traffic_prov = get_prov(traffic_healthy, traffic_log, default_prov=traffic_provider_type)
    weather_prov = get_prov(weather_healthy, weather_log, default_prov="LIVE")
    news_prov = get_prov(news_healthy, news_log, default_prov="LIVE")
    maps_prov = get_prov(maps_healthy, maps_log, default_prov="LIVE")

    feed_availability = {
        "traffic": traffic_healthy,
        "weather": weather_healthy,
        "news": news_healthy,
        "maps": maps_healthy,
    }
    conf_lbl, conf_pct, _ = risk_engine.calculate_confidence(feed_availability)

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    traffic_feed_name = "Live City Traffic Grid" if traffic_provider_type == "LIVE" else "Simulated Traffic Grid"
    traffic_source_desc = (
        "Live Municipal Speed Sensors"
        if traffic_provider_type == "LIVE"
        else f"Physics Engine ({traffic_scenario or 'Baseline Flow'})"
    )

    maps_feed_name = "Geoapify Live Routing" if GEOAPIFY_API_KEY else "OSRM & Nominatim Maps"
    maps_endpoint = "https://api.geoapify.com/v1/routing" if GEOAPIFY_API_KEY else "http://router.project-osrm.org"
    maps_source_desc = "Geoapify Routing Engine & Geocoder" if GEOAPIFY_API_KEY else "OSRM Highway Matrix"

    traffic_freshness = telemetry_logger.get_freshness_metrics("traffic", traffic_prov)
    weather_freshness = telemetry_logger.get_freshness_metrics("weather", weather_prov)
    news_freshness = telemetry_logger.get_freshness_metrics("news", news_prov)
    maps_freshness = telemetry_logger.get_freshness_metrics("maps", maps_prov)

    feeds_detail = [
        FeedTelemetryStatus(
            name=traffic_feed_name,
            source_key="traffic",
            status=traffic_prov,
            freshness=traffic_freshness["freshness"],
            last_successful_update=traffic_freshness["last_successful_update"],
            age_seconds=traffic_freshness["age_seconds"],
            age_formatted=traffic_freshness["age_formatted"],
            latency_ms=traffic_log.latency_ms if traffic_log else 12.0,
            last_timestamp=traffic_log.timestamp if traffic_log else now_iso,
            endpoint="internal://traffic-matrix",
            source_name=traffic_source_desc,
        ),
        FeedTelemetryStatus(
            name="Open-Meteo Weather",
            source_key="weather",
            status=weather_prov,
            freshness=weather_freshness["freshness"],
            last_successful_update=weather_freshness["last_successful_update"],
            age_seconds=weather_freshness["age_seconds"],
            age_formatted=weather_freshness["age_formatted"],
            latency_ms=weather_log.latency_ms if weather_log else 45.0,
            last_timestamp=weather_log.timestamp if weather_log else now_iso,
            endpoint="https://api.open-meteo.com/v1/forecast",
            source_name="WMO / Open-Meteo API",
        ),
        FeedTelemetryStatus(
            name="CAD Police & Incidents",
            source_key="news",
            status=news_prov,
            freshness=news_freshness["freshness"],
            last_successful_update=news_freshness["last_successful_update"],
            age_seconds=news_freshness["age_seconds"],
            age_formatted=news_freshness["age_formatted"],
            latency_ms=news_log.latency_ms if news_log else 8.0,
            last_timestamp=news_log.timestamp if news_log else now_iso,
            endpoint="cad://emergency-alerts-matrix",
            source_name="Emergency CAD Feed",
        ),
        FeedTelemetryStatus(
            name=maps_feed_name,
            source_key="maps",
            status=maps_prov,
            freshness=maps_freshness["freshness"],
            last_successful_update=maps_freshness["last_successful_update"],
            age_seconds=maps_freshness["age_seconds"],
            age_formatted=maps_freshness["age_formatted"],
            latency_ms=maps_log.latency_ms if maps_log else 65.0,
            last_timestamp=maps_log.timestamp if maps_log else now_iso,
            endpoint=maps_endpoint,
            source_name=maps_source_desc,
        ),
    ]

    return DataStatusResponse(
        traffic=traffic_prov.lower(),
        weather=weather_prov.lower(),
        news=news_prov.lower(),
        maps=maps_prov.lower(),
        traffic_provider_type=traffic_provider_type,
        traffic_scenario=traffic_scenario,
        confidence=conf_lbl.lower(),
        confidence_percent=conf_pct,
        feeds_detail=feeds_detail,
    )


@app.post("/api/traffic/scenario", response_model=TrafficScenarioResponse)
def set_traffic_scenario(request: TrafficScenarioRequest) -> TrafficScenarioResponse:
    """
    Hackathon Demo endpoint: Injects traffic demo scenarios (normal, moderate, severe, sudden anomaly)
    or swaps between SimulatedTrafficProvider and RealTrafficProvider.
    """
    if request.provider is not None:
        traffic_service.set_active_provider(request.provider)

    if request.scenario is not None or "scenario" in request.model_fields_set:
        traffic_service.set_scenario_mode(request.scenario)

    provider_type = traffic_service.get_active_provider_type()
    active_scenario = traffic_service.get_scenario_mode()

    msg = f"Traffic mode set to: {provider_type} Provider | Scenario: {active_scenario or 'Baseline Realistic Flow'}"
    return TrafficScenarioResponse(
        status="success",
        provider_type=provider_type,
        active_scenario=active_scenario,
        message=msg,
    )


@app.get("/api/telemetry-logs", response_model=TelemetryLogsResponse)
def get_telemetry_logs(limit: int = 50) -> TelemetryLogsResponse:
    """Returns the most recent external telemetry request and response audit logs."""
    logs_raw = telemetry_logger.get_recent_logs(limit=limit)
    log_dtos = [
        TelemetryLogDTO(
            service_name=entry["service_name"],
            endpoint_url=entry["endpoint_url"],
            request_status=entry["request_status"],
            response_status=entry.get("response_status"),
            timestamp=entry["timestamp"],
            latency_ms=entry["latency_ms"],
            provenance=entry["provenance"],
            success=entry["success"],
            error_message=entry.get("error_message"),
            details=entry.get("details"),
        )
        for entry in logs_raw
    ]
    return TelemetryLogsResponse(total_logs=len(log_dtos), logs=log_dtos)


@app.post("/api/fault-inject", response_model=FaultInjectResponse)
def inject_fault(request: FaultInjectRequest) -> FaultInjectResponse:
    """
    Dev / SIH Demo endpoint: Forces specific feeds to report unavailable
    to demonstrate live graceful degradation and confidence reduction.
    Disabled outside development mode.
    """
    if not SecurityConfig.is_fault_injection_allowed():
        logger.warning(
            "Blocked attempt to invoke development fault-injection endpoint in %s environment.",
            ENVIRONMENT,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Development fault injection is disabled outside development mode.",
        )

    if request.source == "traffic":
        traffic_service.set_online_status(request.enabled)
    elif request.source == "weather":
        weather_service.set_online_status(request.enabled)
    elif request.source == "news":
        news_service.set_online_status(request.enabled)
    elif request.source == "maps":
        routing_service.set_online_status(request.enabled)

    feed_availability = {
        "traffic": traffic_service.is_healthy(),
        "weather": weather_service.is_healthy(),
        "news": news_service.is_healthy(),
        "maps": routing_service.is_healthy(),
    }
    conf_lbl, conf_pct, _ = risk_engine.calculate_confidence(feed_availability)

    return FaultInjectResponse(
        status=f"Source '{request.source}' set to {'ONLINE' if request.enabled else 'UNAVAILABLE'}",
        feed_states=feed_availability,
        confidence_score=conf_pct,
        confidence_label=conf_lbl,
    )


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze_routes(request: AnalyzeRequest, response: Response) -> AnalyzeResponse:
    """
    Evaluates live candidate routes through the full orchestrated pipeline.
    """
    (
        ranked_routes,
        recommended_route,
        overall_feeds,
        explanation_bullets,
        alternatives_avail,
        origin_coords,
        dest_coords,
        all_incidents,
        pipeline_timings,
    ) = run_orchestrated_pipeline(
        source=request.source,
        destination=request.destination,
        vehicle_type=request.vehicle_type,
        priority=request.priority,
    )

    conf_lbl, conf_pct, _ = risk_engine.calculate_confidence(overall_feeds)
    recommended_id = (
        recommended_route.id
        if recommended_route
        else (ranked_routes[0].id if ranked_routes else "route-a")
    )

    profile_data = scoring_engine.get_profile_details(
        vehicle_type=request.vehicle_type,
        priority=request.priority,
    )

    # Attach Server-Timing header for telemetry and debugging
    response.headers["Server-Timing"] = f"total;dur={pipeline_timings.get('total_analyze_ms', 0)}, routing;dur={pipeline_timings.get('routing_geocoding_ms', 0)}, sensor;dur={pipeline_timings.get('sensor_ingestion_ms', 0)}"

    return AnalyzeResponse(
        recommended_route=recommended_id,
        routes=ranked_routes,
        confidence=conf_pct / 100.0,
        confidence_label=conf_lbl,
        confidence_percent=conf_pct,
        explanation=explanation_bullets,
        alternatives_available=alternatives_avail,
        origin_coords=[origin_coords[0], origin_coords[1]],
        destination_coords=[dest_coords[0], dest_coords[1]],
        incidents=all_incidents,
        optimization_profile=MissionProfileDTO(**profile_data),
        pipeline_timings_ms=pipeline_timings,
    )


@app.post("/api/simulate", response_model=SimulateResponse)
def simulate_routes(request: SimulateRequest) -> SimulateResponse:
    """
    Performs what-if stress testing without mutating live telemetry data.
    """
    source = request.source or "Indiranagar, Bengaluru"
    destination = request.destination or "Whitefield, Bengaluru"
    vehicle_type = request.vehicle_type or "Ambulance"
    priority = request.priority or "Critical"

    (
        baseline_routes,
        _,
        _,
        _,
        _,
        origin_coords,
        dest_coords,
        all_incidents,
        pipeline_timings,
    ) = run_orchestrated_pipeline(
        source=source,
        destination=destination,
        vehicle_type=vehicle_type,
        priority=priority,
    )

    sim_response = simulation_agent.run_simulation(
        baseline_routes=baseline_routes,
        request=request,
        origin_coords=[origin_coords[0], origin_coords[1]],
        dest_coords=[dest_coords[0], dest_coords[1]],
    )
    sim_response.incidents = all_incidents

    profile_data = scoring_engine.get_profile_details(
        vehicle_type=vehicle_type,
        priority=priority,
    )
    sim_response.optimization_profile = MissionProfileDTO(**profile_data)
    sim_response.pipeline_timings_ms = pipeline_timings

    return sim_response


@app.get("/api/optimization-profiles")
def get_optimization_profiles():
    """
    Returns all active vehicle mission profile configurations and weights.
    """
    return {
        "profiles": scoring_engine.active_profiles,
        "default": "Ambulance",
    }


@app.post("/api/optimization-profiles/configure")
def configure_optimization_profile(request: ConfigureProfileRequest):
    """
    Updates the weight presets for a specific mission profile at runtime.
    """
    updated = scoring_engine.configure_profile(request.vehicle_type, request.weights)
    return {
        "status": "success",
        "message": f"Updated profile for '{request.vehicle_type}'",
        "profile": updated,
    }


@app.get("/api/ml/metadata", response_model=MLModelMetadataResponse)
def get_ml_model_metadata() -> MLModelMetadataResponse:
    """
    Returns complete ML model metadata, architecture details, feature schema,
    synthetic training provenance, evaluation metrics, and operational limitations.
    """
    meta = get_model_metadata()
    return MLModelMetadataResponse(**meta)


@app.get("/api/demo/scenarios", response_model=DemoScenarioListResponse)
def get_demo_scenarios() -> DemoScenarioListResponse:
    """
    Returns the catalog of 7 standardized SIH demo scenarios for repeatable jury presentations.
    """
    scenarios = demo_service.get_scenarios()
    active = demo_service.get_active_scenario()
    return DemoScenarioListResponse(
        scenarios=scenarios,
        active_scenario=active,
        is_demo_mode=active is not None,
    )


@app.post("/api/demo/activate", response_model=DemoActivateResponse)
def activate_demo_scenario(request: DemoActivateRequest) -> DemoActivateResponse:
    """
    SIH Demo Mode Endpoint: Activates one of the 7 standardized demo scenarios
    producing deterministic, reproducible outputs labeled clearly as DEMO DATA.
    """
    if not SecurityConfig.is_fault_injection_allowed():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo Mode is disabled outside development/demo builds.",
        )

    v_type = request.vehicle_type or "Ambulance"
    prio = request.priority or "Critical"

    scenario_resp, msg = demo_service.generate_scenario_response(
        scenario_id=request.scenario_id,
        vehicle_type=v_type,
        priority=prio,
    )

    scenario_name = next(
        (s.name for s in demo_service.get_scenarios() if s.id == request.scenario_id),
        request.scenario_id,
    )

    return DemoActivateResponse(
        status="success",
        scenario_id=request.scenario_id,
        scenario_name=scenario_name,
        is_demo_data=True,
        analyze_result=scenario_resp,
        message=msg,
    )


@app.post("/api/demo/reset")
def reset_demo_mode():
    """
    Resets demo mode back to live telemetry streaming.
    """
    demo_service.reset_demo_mode()
    return {
        "status": "success",
        "message": "Demo mode reset. Live telemetry pipeline active.",
        "is_demo_mode": False,
    }


