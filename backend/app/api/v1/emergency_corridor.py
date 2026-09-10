"""
REST API Router for Emergency Corridor Simulation & Signal Priority.
Phase 13: Emergency Corridor Simulation.

Provides versioned endpoints under `/api/v1/emergency-corridor` for:
- Service metadata, supported priority algorithms, and decision-support disclaimers
- Preset corridor topologies and emergency vehicle scenarios
- Corridor simulation execution comparing baseline vs priority timing
- Persisted historical simulation runs querying and lifecycle management.
"""
from dataclasses import asdict
from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.session import get_db
from app.models.corridor_simulation import EmergencyCorridorSimulationRun
from app.schemas.emergency_corridor import (
    CorridorConfigSchema,
    CorridorNodeConfigSchema,
    CorridorPresetsResponse,
    EmergencyCorridorDetailResponse,
    EmergencyCorridorInfoResponse,
    EmergencyCorridorListResponse,
    EmergencyCorridorSimulationRequest,
    EmergencyCorridorSummarySchema,
    EmergencyVehicleConfigSchema,
)
from app.services.corridor.data_bridge import CorridorDataBridge
from app.services.corridor.engine import EmergencyCorridorSimulationEngine
from app.services.corridor.models import (
    CorridorConfig,
    CorridorNodeConfig,
    CorridorSimulationResult,
    EmergencyVehicleConfig,
    EmergencyVehicleType,
    PriorityStrategyType,
    RecoveryStrategyType,
)
from app.services.corridor.presets import (
    get_all_corridor_presets,
    get_all_vehicle_presets,
    get_preset_corridor_by_id,
)
from app.services.simulation.models import (
    ApproachConfig,
    ApproachDemand,
    IntersectionConfig,
    SignalPhaseConfig,
)

logger = get_logger(__name__)
router = APIRouter()
simulation_engine = EmergencyCorridorSimulationEngine()


def _convert_schema_to_corridor(cfg: CorridorConfigSchema) -> CorridorConfig:
    """Helper converting Pydantic corridor schema to domain model."""
    nodes: List[CorridorNodeConfig] = []
    for n in cfg.nodes:
        int_cfg = n.intersection
        approaches = [
            ApproachConfig(
                approach_id=a.approach_id,
                name=a.name,
                lanes=a.lanes,
                saturation_flow_rate_per_lane=a.saturation_flow_rate_per_lane,
                target_speed_kmh=a.target_speed_kmh,
            )
            for a in int_cfg.approaches
        ]
        phases = [
            SignalPhaseConfig(
                phase_id=p.phase_id,
                name=p.name,
                controlled_approaches=list(p.controlled_approaches),
                min_green_seconds=p.min_green_seconds,
                max_green_seconds=p.max_green_seconds,
                yellow_seconds=p.yellow_seconds,
                all_red_seconds=p.all_red_seconds,
            )
            for p in int_cfg.phases
        ]
        intersection = IntersectionConfig(
            intersection_id=int_cfg.intersection_id,
            name=int_cfg.name,
            intersection_type=int_cfg.intersection_type,
            approaches=approaches,
            phases=phases,
            cycle_length_min_seconds=int_cfg.cycle_length_min_seconds,
            cycle_length_max_seconds=int_cfg.cycle_length_max_seconds,
            target_cycle_length_seconds=int_cfg.target_cycle_length_seconds,
        )
        demands = [
            ApproachDemand(
                approach_id=d.approach_id,
                vehicle_flow_rate_vph=d.vehicle_flow_rate_vph,
                vehicle_count=d.vehicle_count,
                inbound_count=d.inbound_count,
                outbound_count=d.outbound_count,
                heavy_vehicle_percentage=d.heavy_vehicle_percentage,
                data_provenance=d.data_provenance,
            )
            for d in (n.demands or [])
        ]
        nodes.append(
            CorridorNodeConfig(
                node_id=n.node_id,
                intersection=intersection,
                corridor_approach_id=n.corridor_approach_id,
                exit_approach_id=n.exit_approach_id,
                corridor_phase_id=n.corridor_phase_id,
                distance_to_next_node_m=n.distance_to_next_node_m,
                free_flow_speed_kmh=n.free_flow_speed_kmh,
                demands=demands,
            )
        )
    return CorridorConfig(
        corridor_id=cfg.corridor_id,
        name=cfg.name,
        description=cfg.description,
        nodes=nodes,
    )


def _convert_schema_to_vehicle(v: EmergencyVehicleConfigSchema) -> EmergencyVehicleConfig:
    """Helper converting Pydantic vehicle schema to domain model."""
    return EmergencyVehicleConfig(
        vehicle_id=v.vehicle_id,
        vehicle_type=v.vehicle_type,
        origin_node_id=v.origin_node_id,
        destination_node_id=v.destination_node_id,
        dispatch_time_seconds=v.dispatch_time_seconds,
        cruising_speed_kmh=v.cruising_speed_kmh,
        priority_level=v.priority_level,
        vehicle_length_m=v.vehicle_length_m,
        data_provenance=v.data_provenance,
    )


def _convert_result_to_detail_dict(res: CorridorSimulationResult) -> Dict[str, Any]:
    """Helper formatting CorridorSimulationResult into JSON-serializable structure."""
    nodes_serialized = []
    for n in res.corridor_config.nodes:
        nodes_serialized.append({
            "node_id": n.node_id,
            "intersection": {
                "intersection_id": n.intersection.intersection_id,
                "name": n.intersection.name,
                "intersection_type": n.intersection.intersection_type.value,
                "approaches": [asdict(a) for a in n.intersection.approaches],
                "phases": [
                    {
                        "phase_id": p.phase_id,
                        "name": p.name,
                        "controlled_approaches": p.controlled_approaches,
                        "min_green_seconds": p.min_green_seconds,
                        "max_green_seconds": p.max_green_seconds,
                        "yellow_seconds": p.yellow_seconds,
                        "all_red_seconds": p.all_red_seconds,
                    }
                    for p in n.intersection.phases
                ],
                "cycle_length_min_seconds": n.intersection.cycle_length_min_seconds,
                "cycle_length_max_seconds": n.intersection.cycle_length_max_seconds,
                "target_cycle_length_seconds": n.intersection.target_cycle_length_seconds,
            },
            "corridor_approach_id": n.corridor_approach_id,
            "exit_approach_id": n.exit_approach_id,
            "corridor_phase_id": n.corridor_phase_id,
            "distance_to_next_node_m": n.distance_to_next_node_m,
            "free_flow_speed_kmh": n.free_flow_speed_kmh,
            "demands": [asdict(d) for d in n.demands],
        })

    timelines_serialized = []
    for t in res.node_timelines:
        timelines_serialized.append({
            "node_id": t.node_id,
            "intersection_id": t.intersection_id,
            "intersection_name": t.intersection_name,
            "sequence_index": t.sequence_index,
            "distance_from_origin_m": t.distance_from_origin_m,
            "estimated_arrival_seconds": t.estimated_arrival_seconds,
            "estimated_departure_seconds": t.estimated_departure_seconds,
            "baseline_signal_state_at_arrival": t.baseline_signal_state_at_arrival,
            "priority_signal_state_at_arrival": t.priority_signal_state_at_arrival,
            "baseline_delay_seconds": t.baseline_delay_seconds,
            "priority_delay_seconds": t.priority_delay_seconds,
            "delay_savings_seconds": t.delay_savings_seconds,
            "cross_street_baseline_delay": t.cross_street_baseline_delay,
            "cross_street_priority_delay": t.cross_street_priority_delay,
            "cross_street_delay_delta": t.cross_street_delay_delta,
            "queue_cleared_vehicles": t.queue_cleared_vehicles,
            "priority_window": {
                **asdict(t.priority_window),
                "action_applied": t.priority_window.action_applied.value,
            },
            "recovery_cycles_needed": t.recovery_cycles_needed,
            "baseline_plan": {
                "plan_id": t.baseline_plan.plan_id,
                "plan_type": t.baseline_plan.plan_type,
                "cycle_length_seconds": t.baseline_plan.cycle_length_seconds,
                "total_green_seconds": t.baseline_plan.total_green_seconds,
                "total_lost_seconds": t.baseline_plan.total_lost_seconds,
                "phase_timings": [asdict(pt) for pt in t.baseline_plan.phase_timings],
                "algorithm_name": t.baseline_plan.algorithm_name,
                "description": t.baseline_plan.description,
            },
            "priority_plan": {
                "plan_id": t.priority_plan.plan_id,
                "plan_type": t.priority_plan.plan_type,
                "cycle_length_seconds": t.priority_plan.cycle_length_seconds,
                "total_green_seconds": t.priority_plan.total_green_seconds,
                "total_lost_seconds": t.priority_plan.total_lost_seconds,
                "phase_timings": [asdict(pt) for pt in t.priority_plan.phase_timings],
                "algorithm_name": t.priority_plan.algorithm_name,
                "description": t.priority_plan.description,
            },
            "recovery_plan": {
                "plan_id": t.recovery_plan.plan_id,
                "plan_type": t.recovery_plan.plan_type,
                "cycle_length_seconds": t.recovery_plan.cycle_length_seconds,
                "total_green_seconds": t.recovery_plan.total_green_seconds,
                "total_lost_seconds": t.recovery_plan.total_lost_seconds,
                "phase_timings": [asdict(pt) for pt in t.recovery_plan.phase_timings],
                "algorithm_name": t.recovery_plan.algorithm_name,
                "description": t.recovery_plan.description,
            },
        })

    metrics_dict = {
        **asdict(res.metrics),
        "corridor_los_baseline": res.metrics.corridor_los_baseline.value,
        "corridor_los_priority": res.metrics.corridor_los_priority.value,
    }

    return {
        "id": res.run_id,
        "session_id": None,
        "corridor_name": res.corridor_config.name,
        "corridor_nodes_count": res.corridor_config.node_count,
        "total_distance_meters": res.metrics.total_distance_meters,
        "vehicle_type": res.vehicle_scenario.vehicle_type.value,
        "priority_strategy": res.strategy_type.value,
        "recovery_strategy": res.recovery_strategy.value,
        "data_source": res.data_source,
        "baseline_travel_time_seconds": res.metrics.baseline_corridor_travel_time_seconds,
        "priority_travel_time_seconds": res.metrics.priority_corridor_travel_time_seconds,
        "travel_time_savings_seconds": res.metrics.travel_time_savings_seconds,
        "travel_time_savings_pct": res.metrics.travel_time_savings_pct,
        "baseline_emergency_delay_seconds": res.metrics.baseline_emergency_delay_seconds,
        "priority_emergency_delay_seconds": res.metrics.priority_emergency_delay_seconds,
        "emergency_delay_reduction_pct": res.metrics.emergency_delay_reduction_pct,
        "baseline_cross_street_delay_avg": res.metrics.baseline_cross_street_delay_avg,
        "priority_cross_street_delay_avg": res.metrics.priority_cross_street_delay_avg,
        "cross_street_delay_impact_pct": res.metrics.cross_street_delay_impact_pct,
        "total_recovery_duration_seconds": res.metrics.total_recovery_duration_seconds,
        "total_interventions_count": res.metrics.total_interventions_count,
        "execution_time_ms": res.execution_time_ms,
        "corridor_config": {
            "corridor_id": res.corridor_config.corridor_id,
            "name": res.corridor_config.name,
            "description": res.corridor_config.description,
            "nodes": nodes_serialized,
        },
        "vehicle_scenario": {
            **asdict(res.vehicle_scenario),
            "vehicle_type": res.vehicle_scenario.vehicle_type.value,
        },
        "node_timelines": timelines_serialized,
        "metrics_summary": metrics_dict,
        "simulation_notes": res.simulation_notes,
        "created_at": res.timestamp,
    }


@router.get(
    "/info",
    response_model=EmergencyCorridorInfoResponse,
    summary="Get Emergency Corridor Service Info",
    description="Returns metadata about corridor strategies, safety constraints, vehicle models, and simulation disclaimers.",
)
def get_corridor_info() -> EmergencyCorridorInfoResponse:
    return EmergencyCorridorInfoResponse()


@router.get(
    "/presets",
    response_model=CorridorPresetsResponse,
    summary="Get Corridor and Vehicle Presets",
    description="Returns pre-configured multi-intersection corridor topologies and emergency vehicle response scenarios.",
)
def get_presets() -> CorridorPresetsResponse:
    return CorridorPresetsResponse(
        corridors=get_all_corridor_presets(),
        vehicles=get_all_vehicle_presets(),
    )


@router.post(
    "/simulate",
    response_model=EmergencyCorridorDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Run Emergency Corridor Simulation",
    description="Executes baseline vs coordinated emergency signal priority simulation and returns timeline events and trade-off metrics.",
)
def run_corridor_simulation(
    req: EmergencyCorridorSimulationRequest,
    db: Session = Depends(get_db),
) -> EmergencyCorridorDetailResponse:
    try:
        # 1. Resolve Corridor Configuration
        if req.corridor_preset_id:
            corridor = get_preset_corridor_by_id(req.corridor_preset_id)
            if not corridor:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unknown corridor preset '{req.corridor_preset_id}'.",
                )
        elif req.corridor:
            corridor = _convert_schema_to_corridor(req.corridor)
        else:
            # Default to 3-node medical corridor
            corridor = get_preset_corridor_by_id("corridor_3node_medical")

        # 2. Resolve Vehicle Scenario
        if req.vehicle_preset_id:
            if req.vehicle_preset_id == "ambulance_code_3":
                vehicle = EmergencyVehicleConfig(
                    vehicle_id="AMB-101",
                    vehicle_type=EmergencyVehicleType.AMBULANCE,
                    origin_node_id=corridor.nodes[0].node_id,
                    destination_node_id=corridor.nodes[-1].node_id,
                    dispatch_time_seconds=0.0,
                    cruising_speed_kmh=65.0,
                    priority_level="high",
                )
            elif req.vehicle_preset_id == "fire_truck_heavy":
                vehicle = EmergencyVehicleConfig(
                    vehicle_id="ENG-04",
                    vehicle_type=EmergencyVehicleType.FIRE_TRUCK,
                    origin_node_id=corridor.nodes[0].node_id,
                    destination_node_id=corridor.nodes[-1].node_id,
                    dispatch_time_seconds=5.0,
                    cruising_speed_kmh=55.0,
                    priority_level="critical",
                )
            elif req.vehicle_preset_id == "police_pursuit":
                vehicle = EmergencyVehicleConfig(
                    vehicle_id="POL-22",
                    vehicle_type=EmergencyVehicleType.POLICE,
                    origin_node_id=corridor.nodes[0].node_id,
                    destination_node_id=corridor.nodes[-1].node_id,
                    dispatch_time_seconds=0.0,
                    cruising_speed_kmh=75.0,
                    priority_level="high",
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unknown vehicle preset '{req.vehicle_preset_id}'.",
                )
        elif req.vehicle:
            vehicle = _convert_schema_to_vehicle(req.vehicle)
        else:
            vehicle = EmergencyVehicleConfig(
                origin_node_id=corridor.nodes[0].node_id,
                destination_node_id=corridor.nodes[-1].node_id,
            )

        # 3. Optional DB Session Data Bridging
        extra_notes: List[str] = []
        data_source = "simulation_configured"

        if req.session_id:
            # Populate node 1 demands from DB session
            _, data_source, bridge_notes = CorridorDataBridge.populate_node_demands_from_session(
                db=db,
                session_id=req.session_id,
                node=corridor.nodes[0],
            )
            extra_notes.extend(bridge_notes)

        # 4. Run Simulation
        result = simulation_engine.run_simulation(
            corridor=corridor,
            vehicle=vehicle,
            strategy_type=req.strategy_type,
            recovery_strategy=req.recovery_strategy,
            data_source=data_source,
            extra_notes=extra_notes,
        )

        detail_dict = _convert_result_to_detail_dict(result)
        detail_dict["session_id"] = req.session_id

        # 5. Optional Persistence
        if req.save_to_history:
            db_record = EmergencyCorridorSimulationRun(
                id=result.run_id,
                session_id=req.session_id,
                corridor_name=result.corridor_config.name,
                corridor_nodes_count=result.corridor_config.node_count,
                total_distance_meters=result.metrics.total_distance_meters,
                vehicle_type=result.vehicle_scenario.vehicle_type.value,
                priority_strategy=result.strategy_type.value,
                recovery_strategy=result.recovery_strategy.value,
                data_source=data_source,
                baseline_travel_time_seconds=result.metrics.baseline_corridor_travel_time_seconds,
                priority_travel_time_seconds=result.metrics.priority_corridor_travel_time_seconds,
                travel_time_savings_seconds=result.metrics.travel_time_savings_seconds,
                travel_time_savings_pct=result.metrics.travel_time_savings_pct,
                baseline_emergency_delay_seconds=result.metrics.baseline_emergency_delay_seconds,
                priority_emergency_delay_seconds=result.metrics.priority_emergency_delay_seconds,
                emergency_delay_reduction_pct=result.metrics.emergency_delay_reduction_pct,
                baseline_cross_street_delay_avg=result.metrics.baseline_cross_street_delay_avg,
                priority_cross_street_delay_avg=result.metrics.priority_cross_street_delay_avg,
                cross_street_delay_impact_pct=result.metrics.cross_street_delay_impact_pct,
                total_recovery_duration_seconds=result.metrics.total_recovery_duration_seconds,
                total_interventions_count=result.metrics.total_interventions_count,
                execution_time_ms=result.execution_time_ms,
                corridor_config=detail_dict["corridor_config"],
                vehicle_scenario=detail_dict["vehicle_scenario"],
                node_timelines=detail_dict["node_timelines"],
                metrics_summary=detail_dict["metrics_summary"],
                simulation_notes=detail_dict["simulation_notes"],
                created_at=result.timestamp,
            )
            db.add(db_record)
            db.commit()
            db.refresh(db_record)

        return EmergencyCorridorDetailResponse(**detail_dict)

    except HTTPException:
        raise
    except ValueError as ve:
        logger.warning(f"Validation error in corridor simulation: {str(ve)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Corridor simulation validation error: {str(ve)}",
        )
    except Exception as e:
        logger.error(f"Unexpected error running corridor simulation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal corridor simulation failure.",
        )


@router.get(
    "/runs",
    response_model=EmergencyCorridorListResponse,
    summary="List Historical Corridor Simulation Runs",
    description="Returns a paginated list of persisted emergency corridor simulation runs.",
)
def list_corridor_runs(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    data_source: Optional[str] = Query(None, description="Filter by data source"),
    vehicle_type: Optional[str] = Query(None, description="Filter by vehicle type"),
    strategy: Optional[str] = Query(None, description="Filter by priority strategy"),
    db: Session = Depends(get_db),
) -> EmergencyCorridorListResponse:
    stmt = select(EmergencyCorridorSimulationRun)
    if data_source:
        stmt = stmt.where(EmergencyCorridorSimulationRun.data_source == data_source)
    if vehicle_type:
        stmt = stmt.where(EmergencyCorridorSimulationRun.vehicle_type == vehicle_type)
    if strategy:
        stmt = stmt.where(EmergencyCorridorSimulationRun.priority_strategy == strategy)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    pages = max(1, math.ceil(total / page_size))
    offset = (page - 1) * page_size

    runs = db.scalars(
        stmt.order_by(EmergencyCorridorSimulationRun.created_at.desc())
        .offset(offset)
        .limit(page_size)
    ).all()

    items = [
        EmergencyCorridorSummarySchema(
            id=r.id,
            session_id=r.session_id,
            corridor_name=r.corridor_name,
            corridor_nodes_count=r.corridor_nodes_count,
            total_distance_meters=r.total_distance_meters,
            vehicle_type=r.vehicle_type,
            priority_strategy=r.priority_strategy,
            recovery_strategy=r.recovery_strategy,
            data_source=r.data_source,
            baseline_travel_time_seconds=r.baseline_travel_time_seconds,
            priority_travel_time_seconds=r.priority_travel_time_seconds,
            travel_time_savings_pct=r.travel_time_savings_pct,
            cross_street_delay_impact_pct=r.cross_street_delay_impact_pct,
            execution_time_ms=r.execution_time_ms,
            created_at=r.created_at,
        )
        for r in runs
    ]

    return EmergencyCorridorListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get(
    "/runs/{run_id}",
    response_model=EmergencyCorridorDetailResponse,
    summary="Get Corridor Simulation Run Detail",
    description="Retrieves complete timeline events and comparison metrics for a historical corridor simulation run.",
)
def get_corridor_run_detail(
    run_id: str,
    db: Session = Depends(get_db),
) -> EmergencyCorridorDetailResponse:
    run = db.scalar(
        select(EmergencyCorridorSimulationRun).where(EmergencyCorridorSimulationRun.id == run_id)
    )
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Corridor simulation run '{run_id}' not found.",
        )

    return EmergencyCorridorDetailResponse(
        id=run.id,
        session_id=run.session_id,
        corridor_name=run.corridor_name,
        corridor_nodes_count=run.corridor_nodes_count,
        total_distance_meters=run.total_distance_meters,
        vehicle_type=run.vehicle_type,
        priority_strategy=run.priority_strategy,
        recovery_strategy=run.recovery_strategy,
        data_source=run.data_source,
        baseline_travel_time_seconds=run.baseline_travel_time_seconds,
        priority_travel_time_seconds=run.priority_travel_time_seconds,
        travel_time_savings_seconds=run.travel_time_savings_seconds,
        travel_time_savings_pct=run.travel_time_savings_pct,
        baseline_emergency_delay_seconds=run.baseline_emergency_delay_seconds,
        priority_emergency_delay_seconds=run.priority_emergency_delay_seconds,
        emergency_delay_reduction_pct=run.emergency_delay_reduction_pct,
        baseline_cross_street_delay_avg=run.baseline_cross_street_delay_avg,
        priority_cross_street_delay_avg=run.priority_cross_street_delay_avg,
        cross_street_delay_impact_pct=run.cross_street_delay_impact_pct,
        total_recovery_duration_seconds=run.total_recovery_duration_seconds,
        total_interventions_count=run.total_interventions_count,
        execution_time_ms=run.execution_time_ms,
        corridor_config=run.corridor_config,
        vehicle_scenario=run.vehicle_scenario,
        node_timelines=run.node_timelines,
        metrics_summary=run.metrics_summary,
        simulation_notes=run.simulation_notes,
        created_at=run.created_at,
    )


@router.delete(
    "/runs/{run_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Historical Corridor Simulation Run",
    description="Permanently deletes a historical corridor simulation record.",
)
def delete_corridor_run(
    run_id: str,
    db: Session = Depends(get_db),
):
    run = db.scalar(
        select(EmergencyCorridorSimulationRun).where(EmergencyCorridorSimulationRun.id == run_id)
    )
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Corridor simulation run '{run_id}' not found.",
        )

    db.delete(run)
    db.commit()
    return None
