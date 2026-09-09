"""
Orchestration Engine for Signal Optimization and Simulation.
Phase 12: Traffic Signal Optimization Simulation.

Coordinates intersection validation, baseline generation, mathematical optimization,
simulation evaluation, before/after comparison, and structured provenance documentation.
"""
import time
import uuid
from typing import List, Optional

from app.core.logging import get_logger
from app.services.simulation.baseline import BaselineSignalStrategy
from app.services.simulation.models import (
    ApproachDemand,
    IntersectionConfig,
    OptimizationAlgorithm,
    SignalSimulationResult,
)
from app.services.simulation.objective import SimulationEvaluator
from app.services.simulation.optimizer import SignalOptimizer

logger = get_logger(__name__)


class SignalSimulationEngine:
    """
    Main service orchestrating traffic signal timing optimization and simulation.
    """

    def __init__(self):
        self.baseline_strategy = BaselineSignalStrategy()
        self.optimizer = SignalOptimizer()
        self.evaluator = SimulationEvaluator()

    def run_simulation(
        self,
        intersection: IntersectionConfig,
        demands: List[ApproachDemand],
        algorithm: OptimizationAlgorithm = OptimizationAlgorithm.DEMAND_PROPORTIONAL,
        target_cycle_length: Optional[float] = None,
        data_source: str = "simulation_configured",
        extra_notes: Optional[List[str]] = None,
    ) -> SignalSimulationResult:
        """
        Executes an end-to-end signal optimization simulation run:
        1. Validates intersection topology and traffic demand bounds.
        2. Generates deterministic baseline plan (un-actuated equal split).
        3. Optimizes green-time allocation using selected algorithm.
        4. Runs simulation evaluation on both plans using Webster/HCM models.
        5. Computes granular phase/approach comparisons and percentage deltas.
        6. Measures exact execution runtime.
        """
        start_time = time.perf_counter()
        run_id = f"sim_run_{uuid.uuid4().hex[:12]}"

        logger.info(
            f"Starting signal simulation run '{run_id}' for intersection '{intersection.name}' "
            f"using algorithm '{algorithm.value}' and data_source '{data_source}'."
        )

        # 1. Generate Baseline Signal Plan
        baseline_plan = self.baseline_strategy.generate_baseline_plan(
            intersection=intersection,
            target_cycle_length=target_cycle_length,
        )

        # 2. Generate Optimized Signal Plan
        optimized_plan = self.optimizer.optimize(
            intersection=intersection,
            demands=demands,
            algorithm=algorithm,
            target_cycle_length=target_cycle_length,
        )

        # 3. Simulate and Evaluate Baseline Metrics
        baseline_metrics = self.evaluator.evaluate_plan(
            intersection=intersection,
            demands=demands,
            signal_plan=baseline_plan,
        )

        # 4. Simulate and Evaluate Optimized Metrics
        optimized_metrics = self.evaluator.evaluate_plan(
            intersection=intersection,
            demands=demands,
            signal_plan=optimized_plan,
        )

        # 5. Compare Plans
        (
            phase_comps,
            app_comps,
            delay_red_pct,
            queue_red_pct,
            thru_inc_pct,
            obj_imp_pct,
        ) = self.evaluator.compare_plans(
            intersection=intersection,
            demands=demands,
            baseline_plan=baseline_plan,
            optimized_plan=optimized_plan,
            baseline_metrics=baseline_metrics,
            optimized_metrics=optimized_metrics,
        )

        elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        # Summarize provenance
        provenance_set = {d.data_provenance for d in demands}
        prov_summary = f"Data Source: {data_source} (Approaches: {', '.join(sorted(provenance_set))})"

        notes = list(extra_notes or [])
        notes.append(
            f"Simulation executed in {elapsed_ms:.2f}ms. "
            f"Baseline delay: {baseline_metrics.average_delay_seconds_per_vehicle:.2f}s/veh (LOS {baseline_metrics.intersection_los.value}), "
            f"Optimized delay: {optimized_metrics.average_delay_seconds_per_vehicle:.2f}s/veh (LOS {optimized_metrics.intersection_los.value})."
        )
        notes.append(
            "Advisory decision-support simulation only. Does not connect to or control physical traffic signal controllers."
        )

        return SignalSimulationResult(
            run_id=run_id,
            intersection=intersection,
            demands=demands,
            data_source=data_source,
            algorithm_used=algorithm,
            baseline_plan=baseline_plan,
            optimized_plan=optimized_plan,
            baseline_metrics=baseline_metrics,
            optimized_metrics=optimized_metrics,
            phase_comparisons=phase_comps,
            approach_comparisons=app_comps,
            delay_reduction_pct=delay_red_pct,
            queue_reduction_pct=queue_red_pct,
            throughput_increase_pct=thru_inc_pct,
            objective_improvement_pct=obj_imp_pct,
            execution_time_ms=elapsed_ms,
            data_provenance_summary=prov_summary,
            simulation_notes=notes,
        )
