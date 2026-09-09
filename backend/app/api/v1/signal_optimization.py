"""
REST API Router for Traffic Signal Optimization Simulation.
Phase 12: Traffic Signal Optimization Simulation.

Provides versioned endpoints under `/api/v1/signal-optimization` for:
- System metadata, supported algorithms, and simulation disclaimers
- Preset intersection geometries and demand scenarios
- Optimization and simulation execution
- Persisted historical simulation runs querying and lifecycle management.
"""
from dataclasses import asdict
from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.simulation import SignalSimulationRun
from app.schemas.signal_optimization import (
    ApproachConfigSchema,
    ApproachDemandSchema,
    IntersectionConfigSchema,
    PresetsResponse,
    SignalOptimizationInfoResponse,
    SignalPhaseConfigSchema,
    SignalSimulationDetailResponse,
    SignalSimulationListResponse,
    SignalSimulationRequest,
    SignalSimulationSummarySchema,
)
from app.services.simulation.data_bridge import TrafficDataBridge
from app.services.simulation.engine import SignalSimulationEngine
from app.services.simulation.models import (
    ApproachConfig,
    ApproachDemand,
    IntersectionConfig,
    IntersectionType,
    OptimizationAlgorithm,
    SignalPhaseConfig,
    SignalSimulationResult,
)
from app.services.simulation.presets import (
    build_demand_list,
    get_3way_t_intersection,
    get_all_intersection_presets,
    get_all_scenario_presets,
    get_dual_lane_4way_intersection,
    get_standard_4way_intersection,
)

logger = get_logger(__name__)
router = APIRouter()
simulation_engine = SignalSimulationEngine()


def _convert_schema_to_intersection(cfg: IntersectionConfigSchema) -> IntersectionConfig:
    """Helper converting Pydantic schema to domain model."""
    approaches = [
        ApproachConfig(
            approach_id=a.approach_id,
            name=a.name,
            lanes=a.lanes,
            saturation_flow_rate_per_lane=a.saturation_flow_rate_per_lane,
            target_speed_kmh=a.target_speed_kmh,
        )
        for a in cfg.approaches
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
        for p in cfg.phases
    ]
    return IntersectionConfig(
        intersection_id=cfg.intersection_id,
        name=cfg.name,
        intersection_type=cfg.intersection_type,
        approaches=approaches,
        phases=phases,
        cycle_length_min_seconds=cfg.cycle_length_min_seconds,
        cycle_length_max_seconds=cfg.cycle_length_max_seconds,
        target_cycle_length_seconds=cfg.target_cycle_length_seconds,
    )


def _convert_result_to_detail_dict(res: SignalSimulationResult) -> Dict[str, Any]:
    """Helper formatting SignalSimulationResult into JSON-serializable structure."""
    return {
        "id": res.run_id,
        "session_id": None,
        "intersection_name": res.intersection.name,
        "intersection_type": res.intersection.intersection_type.value,
        "data_source": res.data_source,
        "algorithm_used": res.algorithm_used.value,
        "baseline_cycle_length": res.baseline_plan.cycle_length_seconds,
        "optimized_cycle_length": res.optimized_plan.cycle_length_seconds,
        "baseline_delay_proxy": res.baseline_metrics.average_delay_seconds_per_vehicle,
        "optimized_delay_proxy": res.optimized_metrics.average_delay_seconds_per_vehicle,
        "delay_reduction_pct": res.delay_reduction_pct,
        "baseline_queue_proxy": res.baseline_metrics.total_queue_vehicles,
        "optimized_queue_proxy": res.optimized_metrics.total_queue_vehicles,
        "queue_reduction_pct": res.queue_reduction_pct,
        "baseline_throughput_proxy": res.baseline_metrics.throughput_capacity_vph,
        "optimized_throughput_proxy": res.optimized_metrics.throughput_capacity_vph,
        "throughput_increase_pct": res.throughput_increase_pct,
        "objective_improvement_pct": res.objective_improvement_pct,
        "execution_time_ms": res.execution_time_ms,
        "intersection_config": {
            "intersection_id": res.intersection.intersection_id,
            "name": res.intersection.name,
            "intersection_type": res.intersection.intersection_type.value,
            "approaches": [asdict(a) for a in res.intersection.approaches],
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
                for p in res.intersection.phases
            ],
            "cycle_length_min_seconds": res.intersection.cycle_length_min_seconds,
            "cycle_length_max_seconds": res.intersection.cycle_length_max_seconds,
            "target_cycle_length_seconds": res.intersection.target_cycle_length_seconds,
        },
        "demand_input": [asdict(d) for d in res.demands],
        "baseline_plan": {
            "plan_id": res.baseline_plan.plan_id,
            "plan_type": res.baseline_plan.plan_type,
            "cycle_length_seconds": res.baseline_plan.cycle_length_seconds,
            "total_green_seconds": res.baseline_plan.total_green_seconds,
            "total_lost_seconds": res.baseline_plan.total_lost_seconds,
            "phase_timings": [asdict(pt) for pt in res.baseline_plan.phase_timings],
            "algorithm_name": res.baseline_plan.algorithm_name,
            "description": res.baseline_plan.description,
        },
        "optimized_plan": {
            "plan_id": res.optimized_plan.plan_id,
            "plan_type": res.optimized_plan.plan_type,
            "cycle_length_seconds": res.optimized_plan.cycle_length_seconds,
            "total_green_seconds": res.optimized_plan.total_green_seconds,
            "total_lost_seconds": res.optimized_plan.total_lost_seconds,
            "phase_timings": [asdict(pt) for pt in res.optimized_plan.phase_timings],
            "algorithm_name": res.optimized_plan.algorithm_name,
            "description": res.optimized_plan.description,
        },
        "baseline_metrics": {
            "cycle_length_seconds": res.baseline_metrics.cycle_length_seconds,
            "total_green_seconds": res.baseline_metrics.total_green_seconds,
            "average_delay_seconds_per_vehicle": res.baseline_metrics.average_delay_seconds_per_vehicle,
            "total_queue_vehicles": res.baseline_metrics.total_queue_vehicles,
            "throughput_capacity_vph": res.baseline_metrics.throughput_capacity_vph,
            "critical_v_c_ratio": res.baseline_metrics.critical_v_c_ratio,
            "intersection_los": res.baseline_metrics.intersection_los.value,
            "objective_score": res.baseline_metrics.objective_score,
            "approach_performances": [
                {
                    **asdict(ap),
                    "los_grade": ap.los_grade.value,
                }
                for ap in res.baseline_metrics.approach_performances
            ],
        },
        "optimized_metrics": {
            "cycle_length_seconds": res.optimized_metrics.cycle_length_seconds,
            "total_green_seconds": res.optimized_metrics.total_green_seconds,
            "average_delay_seconds_per_vehicle": res.optimized_metrics.average_delay_seconds_per_vehicle,
            "total_queue_vehicles": res.optimized_metrics.total_queue_vehicles,
            "throughput_capacity_vph": res.optimized_metrics.throughput_capacity_vph,
            "critical_v_c_ratio": res.optimized_metrics.critical_v_c_ratio,
            "intersection_los": res.optimized_metrics.intersection_los.value,
            "objective_score": res.optimized_metrics.objective_score,
            "approach_performances": [
                {
                    **asdict(ap),
                    "los_grade": ap.los_grade.value,
                }
                for ap in res.optimized_metrics.approach_performances
            ],
        },
        "phase_comparisons": [asdict(pc) for pc in res.phase_comparisons],
        "approach_comparisons": [
            {
                **asdict(ac),
                "baseline_los": ac.baseline_los.value,
                "optimized_los": ac.optimized_los.value,
            }
            for ac in res.approach_comparisons
        ],
        "simulation_notes": res.simulation_notes,
        "created_at": res.timestamp,
    }


@router.get(
    "/info",
    response_model=SignalOptimizationInfoResponse,
    summary="Get Signal Optimization Service Info",
    description="Returns metadata about algorithms, objective formulation, constraints, and decision-support disclaimers.",
)
def get_signal_optimization_info() -> SignalOptimizationInfoResponse:
    return SignalOptimizationInfoResponse()


@router.get(
    "/presets",
    response_model=PresetsResponse,
    summary="Get Intersection and Demand Presets",
    description="Returns pre-configured intersection geometries and traffic demand scenarios.",
)
def get_presets() -> PresetsResponse:
    return PresetsResponse(
        intersections=get_all_intersection_presets(),
        scenarios=get_all_scenario_presets(),
    )


@router.post(
    "/simulate",
    response_model=SignalSimulationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Run Traffic Signal Optimization Simulation",
    description="Executes baseline vs optimized signal timing simulation and returns complete before/after metrics.",
)
def run_signal_simulation(
    req: SignalSimulationRequest,
    db: Session = Depends(get_db),
) -> SignalSimulationDetailResponse:
    try:
        # 1. Resolve Intersection Configuration
        if req.intersection_preset_id:
            preset_id = req.intersection_preset_id
            if preset_id == "int_4way_standard":
                intersection = get_standard_4way_intersection()
            elif preset_id == "int_4way_dual_lane":
                intersection = get_dual_lane_4way_intersection()
            elif preset_id == "int_3way_t_junction":
                intersection = get_3way_t_intersection()
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unknown intersection preset '{preset_id}'.",
                )
        elif req.intersection:
            intersection = _convert_schema_to_intersection(req.intersection)
        else:
            # Default to standard 4-way
            intersection = get_standard_4way_intersection()

        # 2. Resolve Demands and Data Provenance
        extra_notes: List[str] = []
        data_source = "simulation_configured"

        if req.session_id:
            demands, data_source, bridge_notes = TrafficDataBridge.extract_demand_from_session(
                db=db,
                session_id=req.session_id,
                intersection=intersection,
            )
            extra_notes.extend(bridge_notes)
        elif req.demand_scenario_id:
            app_ids = [a.approach_id for a in intersection.approaches]
            demands = build_demand_list(
                scenario_key=req.demand_scenario_id,
                approach_ids=app_ids,
                provenance="simulation_configured",
            )
            data_source = "simulation_configured"
            extra_notes.append(f"Loaded preset demand scenario '{req.demand_scenario_id}'.")
        elif req.demands:
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
                for d in req.demands
            ]
            provs = {d.data_provenance for d in demands}
            data_source = provs.pop() if len(provs) == 1 else "simulation_configured"
        else:
            # Default to balanced moderate
            app_ids = [a.approach_id for a in intersection.approaches]
            demands = build_demand_list("balanced_moderate", app_ids)
            data_source = "simulation_configured"

        # 3. Run Simulation
        result = simulation_engine.run_simulation(
            intersection=intersection,
            demands=demands,
            algorithm=req.algorithm,
            target_cycle_length=req.target_cycle_length,
            data_source=data_source,
            extra_notes=extra_notes,
        )

        detail_dict = _convert_result_to_detail_dict(result)
        detail_dict["session_id"] = req.session_id

        # 4. Optional Persistence to History
        if req.save_to_history:
            db_record = SignalSimulationRun(
                id=result.run_id,
                session_id=req.session_id,
                intersection_name=result.intersection.name,
                intersection_type=result.intersection.intersection_type.value,
                data_source=data_source,
                algorithm_used=result.algorithm_used.value,
                baseline_cycle_length=result.baseline_plan.cycle_length_seconds,
                optimized_cycle_length=result.optimized_plan.cycle_length_seconds,
                baseline_delay_proxy=result.baseline_metrics.average_delay_seconds_per_vehicle,
                optimized_delay_proxy=result.optimized_metrics.average_delay_seconds_per_vehicle,
                delay_reduction_pct=result.delay_reduction_pct,
                baseline_queue_proxy=result.baseline_metrics.total_queue_vehicles,
                optimized_queue_proxy=result.optimized_metrics.total_queue_vehicles,
                queue_reduction_pct=result.queue_reduction_pct,
                baseline_throughput_proxy=result.baseline_metrics.throughput_capacity_vph,
                optimized_throughput_proxy=result.optimized_metrics.throughput_capacity_vph,
                throughput_increase_pct=result.throughput_increase_pct,
                objective_improvement_pct=result.objective_improvement_pct,
                execution_time_ms=result.execution_time_ms,
                intersection_config=detail_dict["intersection_config"],
                demand_input=detail_dict["demand_input"],
                baseline_plan=detail_dict["baseline_plan"],
                optimized_plan=detail_dict["optimized_plan"],
                baseline_metrics=detail_dict["baseline_metrics"],
                optimized_metrics=detail_dict["optimized_metrics"],
                phase_comparisons=detail_dict["phase_comparisons"],
                approach_comparisons=detail_dict["approach_comparisons"],
                simulation_notes=detail_dict["simulation_notes"],
                created_at=result.timestamp,
            )
            db.add(db_record)
            db.commit()
            db.refresh(db_record)

        return SignalSimulationDetailResponse(**detail_dict)

    except HTTPException:
        raise
    except ValueError as ve:
        logger.warning(f"Validation error in signal simulation: {str(ve)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Simulation validation error: {str(ve)}",
        )
    except Exception as e:
        logger.error(f"Unexpected error running signal simulation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal signal simulation failure.",
        )


@router.post(
    "/optimize",
    response_model=SignalSimulationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Alias for /simulate",
    description="Alternative endpoint for executing signal optimization simulation.",
)
def run_signal_optimize_alias(
    req: SignalSimulationRequest,
    db: Session = Depends(get_db),
) -> SignalSimulationDetailResponse:
    return run_signal_simulation(req, db)


@router.get(
    "/runs",
    response_model=SignalSimulationListResponse,
    summary="List Historical Simulation Runs",
    description="Returns a paginated list of persisted signal optimization simulation runs.",
)
def list_simulation_runs(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    data_source: Optional[str] = Query(None, description="Filter by data source"),
    algorithm: Optional[str] = Query(None, description="Filter by algorithm used"),
    db: Session = Depends(get_db),
) -> SignalSimulationListResponse:
    stmt = select(SignalSimulationRun)
    if data_source:
        stmt = stmt.where(SignalSimulationRun.data_source == data_source)
    if algorithm:
        stmt = stmt.where(SignalSimulationRun.algorithm_used == algorithm)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    pages = max(1, math.ceil(total / page_size))
    offset = (page - 1) * page_size

    runs = db.scalars(
        stmt.order_by(SignalSimulationRun.created_at.desc())
        .offset(offset)
        .limit(page_size)
    ).all()

    items = [
        SignalSimulationSummarySchema(
            id=r.id,
            session_id=r.session_id,
            intersection_name=r.intersection_name,
            intersection_type=r.intersection_type,
            data_source=r.data_source,
            algorithm_used=r.algorithm_used,
            baseline_cycle_length=r.baseline_cycle_length,
            optimized_cycle_length=r.optimized_cycle_length,
            baseline_delay_proxy=r.baseline_delay_proxy,
            optimized_delay_proxy=r.optimized_delay_proxy,
            delay_reduction_pct=r.delay_reduction_pct,
            objective_improvement_pct=r.objective_improvement_pct,
            execution_time_ms=r.execution_time_ms,
            created_at=r.created_at,
        )
        for r in runs
    ]

    return SignalSimulationListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get(
    "/runs/{run_id}",
    response_model=SignalSimulationDetailResponse,
    summary="Get Simulation Run Details",
    description="Retrieves complete before/after metrics and plan data for a historical simulation run.",
)
def get_simulation_run_detail(
    run_id: str,
    db: Session = Depends(get_db),
) -> SignalSimulationDetailResponse:
    run = db.scalar(
        select(SignalSimulationRun).where(SignalSimulationRun.id == run_id)
    )
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation run '{run_id}' not found.",
        )

    return SignalSimulationDetailResponse(
        id=run.id,
        session_id=run.session_id,
        intersection_name=run.intersection_name,
        intersection_type=run.intersection_type,
        data_source=run.data_source,
        algorithm_used=run.algorithm_used,
        baseline_cycle_length=run.baseline_cycle_length,
        optimized_cycle_length=run.optimized_cycle_length,
        baseline_delay_proxy=run.baseline_delay_proxy,
        optimized_delay_proxy=run.optimized_delay_proxy,
        delay_reduction_pct=run.delay_reduction_pct,
        baseline_queue_proxy=run.baseline_queue_proxy,
        optimized_queue_proxy=run.optimized_queue_proxy,
        queue_reduction_pct=run.queue_reduction_pct,
        baseline_throughput_proxy=run.baseline_throughput_proxy,
        optimized_throughput_proxy=run.optimized_throughput_proxy,
        throughput_increase_pct=run.throughput_increase_pct,
        objective_improvement_pct=run.objective_improvement_pct,
        execution_time_ms=run.execution_time_ms,
        intersection_config=run.intersection_config,
        demand_input=run.demand_input,
        baseline_plan=run.baseline_plan,
        optimized_plan=run.optimized_plan,
        baseline_metrics=run.baseline_metrics,
        optimized_metrics=run.optimized_metrics,
        phase_comparisons=run.phase_comparisons,
        approach_comparisons=run.approach_comparisons,
        simulation_notes=run.simulation_notes,
        created_at=run.created_at,
    )


@router.delete(
    "/runs/{run_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Historical Simulation Run",
    description="Permanently deletes a historical signal optimization simulation record.",
)
def delete_simulation_run(
    run_id: str,
    db: Session = Depends(get_db),
):
    run = db.scalar(
        select(SignalSimulationRun).where(SignalSimulationRun.id == run_id)
    )
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation run '{run_id}' not found.",
        )

    db.delete(run)
    db.commit()
    return None
