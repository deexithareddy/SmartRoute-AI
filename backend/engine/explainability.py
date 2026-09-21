"""
Explainability Engine

Generates mathematically grounded, natural language decision rationale built strictly
from evaluated route metrics, multi-criteria trade-offs, and telemetry health states.

Explains both:
  1. WHY THE RECOMMENDED ROUTE WAS SELECTED
  2. WHY OTHER ROUTES WERE NOT SELECTED
"""

from typing import Dict, List, Optional, Any
from backend.models.schemas import RouteResult
from backend.engine.risk_engine import risk_engine


class ExplainabilityEngine:
    """
    Constructs transparent, data-grounded explanations for emergency route recommendations.
    """

    def generate_recommendation_explanation(
        self,
        recommended_route: RouteResult,
        all_routes: List[RouteResult],
        feed_availability: Dict[str, bool],
        vehicle_type: str = "Ambulance",
        priority: str = "Critical",
    ) -> List[str]:
        """
        Generates a structured bullet-point explanation derived directly from candidate route comparisons:
          - Explains why the recommended route was selected
          - Explains why each alternative route was not selected
        """
        if not recommended_route:
            return ["No candidate routes available for evaluation."]

        bullets: List[str] = []

        # Find the fastest route among candidates
        fastest_route = (
            min(all_routes, key=lambda r: r.eta_minutes) if all_routes else recommended_route
        )
        non_rec_routes = [r for r in all_routes if r.id != recommended_route.id]

        # ======================================================================
        # SECTION 1: WHY THE RECOMMENDED ROUTE WAS SELECTED
        # ======================================================================
        bullets.append(f"{recommended_route.code} recommended because:")

        # 1. Combined Route Score
        if recommended_route.overall_score is not None:
            bullets.append(
                f"• Lowest combined route score ({recommended_route.overall_score:.2f}) across multi-criteria weights"
            )
        else:
            bullets.append("• Optimal multi-criteria score balancing speed, safety, and reliability")

        # 2. Traffic Risk & Anomaly Avoidance
        rec_traffic = float(recommended_route.risk_factors.traffic)
        alt_with_higher_traffic = [
            r for r in non_rec_routes if float(r.risk_factors.traffic) > rec_traffic + 0.10
        ]
        alt_with_anom = [
            r for r in non_rec_routes if (r.traffic_anomaly and r.traffic_anomaly.get("has_anomaly"))
        ]

        if alt_with_anom:
            bullets.append(
                f"• Bypasses severe traffic anomaly impacting {alt_with_anom[0].code}"
            )
        elif alt_with_higher_traffic:
            primary_higher = alt_with_higher_traffic[0]
            p_traffic = float(primary_higher.risk_factors.traffic)
            diff_pct = int(round(((p_traffic - rec_traffic) / max(0.01, p_traffic)) * 100))
            bullets.append(f"• {diff_pct}% lower traffic risk than {primary_higher.code}")
        elif rec_traffic <= 0.25:
            bullets.append(f"• Lower traffic risk ({int(round(rec_traffic * 100))}% congestion exposure)")
        else:
            bullets.append(f"• Manageable traffic congestion ({int(round(rec_traffic * 100))}%)")

        # 3. Incident & Disruption Status
        rec_incident = float(recommended_route.risk_factors.incident)
        alt_with_incidents = [
            r for r in non_rec_routes if float(r.risk_factors.incident) > 0.0 or (r.incidents and len(r.incidents) > 0)
        ]

        if rec_incident == 0.0:
            if alt_with_incidents:
                bullets.append(
                    f"• Avoids active incident / road disruption reported on {alt_with_incidents[0].code}"
                )
            else:
                bullets.append("• No confirmed incidents or emergency lane blockages")
        else:
            bullets.append(f"• Moderate incident exposure ({int(round(rec_incident * 100))}%)")

        # 4. Weather Exposure
        rec_weather = float(recommended_route.risk_factors.weather)
        alt_with_higher_weather = [
            r for r in non_rec_routes if float(r.risk_factors.weather) > rec_weather + 0.10
        ]
        if alt_with_higher_weather:
            bullets.append(
                f"• Lower weather hazard exposure than {alt_with_higher_weather[0].code} ({int(round(rec_weather * 100))}% vs {int(round(float(alt_with_higher_weather[0].risk_factors.weather) * 100))}%)"
            )
        elif rec_weather <= 0.25:
            bullets.append("• Favorable weather conditions along corridor")

        # 5. Travel Time / ETA Trade-off
        if recommended_route.id == fastest_route.id:
            bullets.append(f"• Fastest candidate route ({recommended_route.eta_minutes} min ETA)")
        else:
            eta_diff = recommended_route.eta_minutes - fastest_route.eta_minutes
            bullets.append(
                f"• Acceptable ETA (only {eta_diff} minutes slower than fastest route {fastest_route.code})"
            )

        # 6. Telemetry Health & Data Confidence
        conf_lbl, conf_pct, _ = risk_engine.calculate_confidence(feed_availability)
        unavailable_feeds = [
            name.capitalize() for name, is_live in feed_availability.items() if not is_live
        ]
        if not unavailable_feeds:
            bullets.append(f"• High confidence in current telemetry ({conf_pct}% data coverage)")
        else:
            missing_str = ", ".join(unavailable_feeds)
            bullets.append(
                f"• {missing_str} telemetry unavailable — recommendation carries {conf_lbl.lower()} confidence ({conf_pct}%)"
            )

        # ======================================================================
        # SECTION 2: WHY OTHER ROUTES WERE NOT SELECTED
        # ======================================================================
        if not non_rec_routes:
            bullets.append("")
            bullets.append("Alternative corridors:")
            bullets.append("• Only one viable corridor found — no alternative routes currently available to compare.")
        else:
            for route in non_rec_routes:
                bullets.append("")  # Blank spacer
                bullets.append(f"{route.code} not selected because:")

                is_closed = (
                    route.is_passable is False
                    or route.status == "CRITICAL"
                    or route.risk_percent == 100
                    or "closed" in route.name.lower()
                )

                # Road closure condition
                if is_closed:
                    bullets.append("• Corridor blocked by simulated road closure (impassable)")
                    bullets.append("• Critical risk score (Emergency transit prohibited)")
                    continue

                # ETA factor
                if route.eta_minutes < recommended_route.eta_minutes:
                    diff = recommended_route.eta_minutes - route.eta_minutes
                    bullets.append(f"• {diff} minutes faster, but penalized heavily by risk/delay")
                elif route.eta_minutes > recommended_route.eta_minutes:
                    diff = route.eta_minutes - recommended_route.eta_minutes
                    bullets.append(f"• Longer ETA (+{diff} minutes slower than recommended route)")

                # Traffic Anomaly or Traffic Congestion
                if route.traffic_anomaly and route.traffic_anomaly.get("has_anomaly"):
                    obs = route.traffic_anomaly.get("observed_speed", 0)
                    exp = route.traffic_anomaly.get("expected_speed", 0)
                    cause = route.traffic_anomaly.get("cause", "UNKNOWN")
                    bullets.append(
                        f"• Severe traffic anomaly detected ({obs:.0f} km/h vs {exp:.0f} km/h expected, cause: {cause})"
                    )
                elif float(route.risk_factors.traffic) > rec_traffic + 0.08:
                    bullets.append(
                        f"• Higher traffic risk ({int(round(float(route.risk_factors.traffic) * 100))}% vs {int(round(rec_traffic * 100))}%)"
                    )
                elif float(route.risk_factors.traffic) < rec_traffic - 0.08:
                    bullets.append(
                        f"• Lowest traffic risk ({int(round(float(route.risk_factors.traffic) * 100))}%), but outweighed by other factors"
                    )

                # Active Incidents
                if route.incidents and len(route.incidents) > 0:
                    inc = route.incidents[0]
                    bullets.append(f"• Confirmed incident: {inc.headline}")
                elif float(route.risk_factors.incident) > 0.15:
                    bullets.append(
                        f"• Active incident hazard ({int(round(float(route.risk_factors.incident) * 100))}% risk)"
                    )

                # Weather Hazard
                if float(route.risk_factors.weather) > rec_weather + 0.10:
                    bullets.append(
                        f"• Higher weather risk ({int(round(float(route.risk_factors.weather) * 100))}% vs {int(round(rec_weather * 100))}%)"
                    )

                # Predicted Delay
                rec_delay = (
                    recommended_route.predicted_delay_minutes
                    if recommended_route.predicted_delay_minutes is not None
                    else 0.0
                )
                r_delay = (
                    route.predicted_delay_minutes
                    if route.predicted_delay_minutes is not None
                    else 0.0
                )
                if r_delay > rec_delay + 2.0:
                    bullets.append(f"• Higher predicted delay (+{r_delay:.1f} min vs +{rec_delay:.1f} min)")

                # Reliability
                if route.reliability_score < recommended_route.reliability_score - 0.10:
                    bullets.append(
                        f"• Lower reliability ({int(round(route.reliability_score * 100))}% vs {int(round(recommended_route.reliability_score * 100))}%)"
                    )

                # Overall Score
                if (
                    route.overall_score is not None
                    and recommended_route.overall_score is not None
                    and route.overall_score > recommended_route.overall_score
                ):
                    bullets.append(
                        f"• Higher combined route penalty score ({route.overall_score:.2f} vs {recommended_route.overall_score:.2f})"
                    )

        return bullets

    def generate_structured_explanations(
        self,
        recommended_route: RouteResult,
        all_routes: List[RouteResult],
        feed_availability: Dict[str, bool],
        vehicle_type: str = "Ambulance",
        priority: str = "Critical",
    ) -> Dict[str, Any]:
        """
        Returns structured dictionary separating reasons for recommendation vs non-selection.
        """
        raw_bullets = self.generate_recommendation_explanation(
            recommended_route=recommended_route,
            all_routes=all_routes,
            feed_availability=feed_availability,
            vehicle_type=vehicle_type,
            priority=priority,
        )

        sections: List[Dict[str, Any]] = []
        current_title = ""
        current_reasons: List[str] = []

        for line in raw_bullets:
            if not line.strip():
                if current_title:
                    sections.append({"title": current_title, "reasons": current_reasons})
                    current_title = ""
                    current_reasons = []
            elif line.endswith("because:"):
                if current_title:
                    sections.append({"title": current_title, "reasons": current_reasons})
                current_title = line
                current_reasons = []
            elif line.startswith("•"):
                current_reasons.append(line.lstrip("•").strip())
            else:
                current_reasons.append(line.strip())

        if current_title:
            sections.append({"title": current_title, "reasons": current_reasons})

        return {
            "recommended_route_id": recommended_route.id if recommended_route else None,
            "sections": sections,
            "raw_bullets": raw_bullets,
        }


# Singleton instance
explainability_engine = ExplainabilityEngine()
