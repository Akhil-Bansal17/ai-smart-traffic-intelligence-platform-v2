"""
Data Bridge connecting Video Analysis Sessions to Signal Simulation Demands.
Phase 12: Traffic Signal Optimization Simulation.

Extracts traffic flow rates, directional splits, and heavy vehicle ratios from
persisted database analysis sessions, adhering to strict 4-way data provenance.
"""
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.analysis import AnalysisSession, TrafficMetricsRecord
from app.services.simulation.models import ApproachDemand, IntersectionConfig


class TrafficDataBridge:
    """
    Translates real or synthetic video analysis metrics into structured ApproachDemand inputs.
    Strictly documents data provenance and flags unobserved approaches.
    """

    @staticmethod
    def extract_demand_from_session(
        db: Session,
        session_id: str,
        intersection: IntersectionConfig,
        cross_street_flow_vph: float = 300.0,
    ) -> Tuple[List[ApproachDemand], str, List[str]]:
        """
        Loads an AnalysisSession and maps its traffic metrics to intersection approaches.
        Returns:
            - List of ApproachDemand
            - Provenance tag ('real_database_metrics' or 'synthetic_pipeline_metrics')
            - Explanatory notes regarding data mapping and unobserved approaches.
        """
        session = db.scalar(
            select(AnalysisSession).where(AnalysisSession.id == session_id)
        )
        if not session:
            raise ValueError(f"Analysis session '{session_id}' not found.")

        if not session.traffic_metrics:
            raise ValueError(f"Analysis session '{session_id}' contains no traffic metrics.")

        metrics: TrafficMetricsRecord = session.traffic_metrics
        video = session.video

        # Determine provenance under strict trust boundary
        is_genuine_real = False
        provenance = "synthetic_pipeline_metrics"

        if video:
            src_type = getattr(video, "source_type", "unknown")
            is_prov_verified = getattr(video, "provenance_verified", False) is True
            has_src_ref = bool(getattr(video, "source_reference", None))

            if src_type == "real_world" and is_prov_verified and has_src_ref:
                is_genuine_real = True
                provenance = "real_database_metrics"
            else:
                provenance = "synthetic_pipeline_metrics"

        # Extract flow metrics
        hourly_flow = float(metrics.flow_rate_per_hour)
        total_vol = int(metrics.total_volume)

        # Directional split
        inbound_count = 0
        outbound_count = 0
        for d in (metrics.direction_distribution or []):
            if d.get("direction") == "inbound":
                inbound_count = int(d.get("count", 0))
            elif d.get("direction") == "outbound":
                outbound_count = int(d.get("count", 0))

        tot_dir = max(1, inbound_count + outbound_count)
        inbound_ratio = inbound_count / float(tot_dir) if tot_dir > 0 else 0.5
        outbound_ratio = outbound_count / float(tot_dir) if tot_dir > 0 else 0.5

        inbound_vph = hourly_flow * inbound_ratio
        outbound_vph = hourly_flow * outbound_ratio

        # Heavy vehicle percentage
        heavy_count = 0
        for c in (metrics.class_distribution or []):
            c_name = str(c.get("class_name", "")).lower()
            if c_name in ("bus", "truck"):
                heavy_count += int(c.get("count", 0))
        heavy_pct = (heavy_count / max(1, total_vol)) * 100.0

        # Map to intersection approaches
        demands: List[ApproachDemand] = []
        notes: List[str] = []

        # Single camera perspective note:
        notes.append(
            f"Extracted {total_vol} vehicles ({hourly_flow:.1f} veh/hr) from session {session_id[:8]} "
            f"with provenance '{provenance}'."
        )

        app_ids = [a.approach_id for a in intersection.approaches]

        # Inbound -> North, Outbound -> South
        if "north" in app_ids:
            demands.append(
                ApproachDemand(
                    approach_id="north",
                    vehicle_flow_rate_vph=round(max(50.0, inbound_vph), 1),
                    vehicle_count=inbound_count,
                    inbound_count=inbound_count,
                    outbound_count=0,
                    heavy_vehicle_percentage=round(heavy_pct, 1),
                    data_provenance=provenance,
                )
            )
        if "south" in app_ids:
            demands.append(
                ApproachDemand(
                    approach_id="south",
                    vehicle_flow_rate_vph=round(max(50.0, outbound_vph), 1),
                    vehicle_count=outbound_count,
                    inbound_count=0,
                    outbound_count=outbound_count,
                    heavy_vehicle_percentage=round(heavy_pct, 1),
                    data_provenance=provenance,
                )
            )

        # Cross street approaches (e.g. East / West) not in camera frame are filled with configured simulation input
        for a_id in app_ids:
            if a_id not in ("north", "south"):
                demands.append(
                    ApproachDemand(
                        approach_id=a_id,
                        vehicle_flow_rate_vph=float(cross_street_flow_vph),
                        vehicle_count=int(cross_street_flow_vph / 12),
                        inbound_count=int(cross_street_flow_vph / 12),
                        outbound_count=0,
                        heavy_vehicle_percentage=2.5,
                        data_provenance="simulation_configured",
                    )
                )
                notes.append(
                    f"Approach '{a_id}' was outside camera FOV; initialized with configured simulation demand "
                    f"({cross_street_flow_vph:.0f} veh/hr, data_provenance='simulation_configured')."
                )

        return demands, provenance, notes
