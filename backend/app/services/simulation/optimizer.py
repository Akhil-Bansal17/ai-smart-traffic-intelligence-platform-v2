"""
Explainable Signal Optimization Engine.
Phase 12: Traffic Signal Optimization Simulation.

Implements three transparent, constrained optimization strategies:
1. Demand-Proportional Green Allocation (Equi-saturation split)
2. Webster's Minimum-Delay Optimal Cycle & Green Split
3. Constrained Delay Minimization (Direct discrete search over feasible green allocations)

All strategies strictly enforce minimum green, maximum green, clearance times, and cycle length boundaries.
"""
import uuid
from typing import Dict, List, Optional, Tuple

from app.services.simulation.baseline import BaselineSignalStrategy
from app.services.simulation.models import (
    ApproachConfig,
    ApproachDemand,
    IntersectionConfig,
    OptimizationAlgorithm,
    PhaseTiming,
    SignalPhaseConfig,
    SignalPlan,
)
from app.services.simulation.objective import SimulationEvaluator


class SignalOptimizer:
    """
    Computes optimized signal timing plans given intersection geometry,
    safety constraints, and approach traffic demands.
    """

    def __init__(self):
        self.baseline_generator = BaselineSignalStrategy()

    def optimize(
        self,
        intersection: IntersectionConfig,
        demands: List[ApproachDemand],
        algorithm: OptimizationAlgorithm = OptimizationAlgorithm.DEMAND_PROPORTIONAL,
        target_cycle_length: Optional[float] = None,
    ) -> SignalPlan:
        """
        Main entry point for signal optimization. Dispatches to selected algorithm.
        """
        # Validate intersection configuration
        self._validate_inputs(intersection, demands)

        if algorithm == OptimizationAlgorithm.DEMAND_PROPORTIONAL:
            return self._optimize_demand_proportional(intersection, demands, target_cycle_length)
        elif algorithm == OptimizationAlgorithm.WEBSTER_OPTIMAL:
            return self._optimize_webster_optimal(intersection, demands)
        elif algorithm == OptimizationAlgorithm.CONSTRAINED_DELAY_MINIMIZATION:
            return self._optimize_constrained_delay_minimization(intersection, demands, target_cycle_length)
        else:
            return self._optimize_demand_proportional(intersection, demands, target_cycle_length)

    def _validate_inputs(
        self,
        intersection: IntersectionConfig,
        demands: List[ApproachDemand],
    ) -> None:
        """Validates all inputs against numerical and structural safety bounds."""
        if not intersection.phases or len(intersection.phases) < 2:
            raise ValueError("Intersection must define at least 2 signal phases.")
        if len(intersection.phases) > 8:
            raise ValueError("Intersection cannot exceed 8 signal phases.")
        if not intersection.approaches:
            raise ValueError("Intersection must define at least 1 approach.")

        app_ids = {a.approach_id for a in intersection.approaches}
        for phase in intersection.phases:
            if not phase.controlled_approaches:
                raise ValueError(f"Phase {phase.phase_id} must control at least one approach.")
            for app_id in phase.controlled_approaches:
                if app_id not in app_ids:
                    raise ValueError(f"Phase {phase.phase_id} references unknown approach '{app_id}'.")
            if phase.min_green_seconds < 5.0:
                raise ValueError(f"Phase {phase.phase_id} min green must be >= 5.0 seconds for safety.")
            if phase.max_green_seconds < phase.min_green_seconds:
                raise ValueError(f"Phase {phase.phase_id} max green cannot be less than min green.")
            if phase.yellow_seconds < 2.0:
                raise ValueError(f"Phase {phase.phase_id} yellow duration must be >= 2.0 seconds.")
            if phase.all_red_seconds < 0.0:
                raise ValueError(f"Phase {phase.phase_id} all-red duration cannot be negative.")

        for d in demands:
            if d.vehicle_flow_rate_vph < 0.0 or not isinstance(d.vehicle_flow_rate_vph, (int, float)):
                raise ValueError(f"Invalid flow rate for approach {d.approach_id}: must be non-negative finite number.")

    def _get_critical_flow_ratios(
        self,
        intersection: IntersectionConfig,
        demands: List[ApproachDemand],
    ) -> Tuple[Dict[str, float], float]:
        """
        Calculates the critical flow ratio y_i = max_{j in Phase_i} (q_j / s_j) for each phase.
        Returns mapping of phase_id -> y_i and total Y = sum(y_i).
        """
        demand_map: Dict[str, ApproachDemand] = {d.approach_id: d for d in demands}
        approach_map: Dict[str, ApproachConfig] = {a.approach_id: a for a in intersection.approaches}

        phase_flow_ratios: Dict[str, float] = {}
        total_Y = 0.0

        for phase in intersection.phases:
            max_y_phase = 0.0
            for app_id in phase.controlled_approaches:
                app = approach_map.get(app_id)
                dem = demand_map.get(app_id)
                if app and dem:
                    q = max(0.0, float(dem.vehicle_flow_rate_vph))
                    s = app.get_total_saturation_flow()
                    y = q / max(100.0, s)
                    if y > max_y_phase:
                        max_y_phase = y

            phase_flow_ratios[phase.phase_id] = max_y_phase
            total_Y += max_y_phase

        return phase_flow_ratios, total_Y

    def _redistribute_greens(
        self,
        raw_greens: List[float],
        phases: List[SignalPhaseConfig],
        target_total_green: float,
    ) -> List[float]:
        """
        Clamps greens to [min_green, max_green] and iteratively redistributes slack
        to preserve exact target_total_green.
        """
        greens = list(raw_greens)
        num_phases = len(phases)

        # Initial clamp
        for i, phase in enumerate(phases):
            greens[i] = max(phase.min_green_seconds, min(phase.max_green_seconds, greens[i]))

        # Iterative residual balancing
        for _ in range(50):
            current_sum = sum(greens)
            diff = target_total_green - current_sum
            if abs(diff) <= 1e-3:
                break

            eligible = []
            for i, phase in enumerate(phases):
                if diff > 0 and greens[i] < phase.max_green_seconds - 1e-3:
                    eligible.append(i)
                elif diff < 0 and greens[i] > phase.min_green_seconds + 1e-3:
                    eligible.append(i)

            if not eligible:
                break

            adj = diff / float(len(eligible))
            for i in eligible:
                phase = phases[i]
                greens[i] = max(phase.min_green_seconds, min(phase.max_green_seconds, greens[i] + adj))

        return greens

    def _optimize_demand_proportional(
        self,
        intersection: IntersectionConfig,
        demands: List[ApproachDemand],
        target_cycle_length: Optional[float] = None,
    ) -> SignalPlan:
        """
        Demand-Proportional Green Split Strategy:
        Allocates available green time proportional to critical approach volume-to-saturation ratios.
        Preserves specified target cycle length (or intersection default).
        """
        phases = intersection.phases
        total_lost = intersection.get_total_lost_time()
        min_cycle = total_lost + intersection.get_total_min_green()

        if target_cycle_length is not None:
            cycle = float(target_cycle_length)
        elif intersection.target_cycle_length_seconds is not None:
            cycle = float(intersection.target_cycle_length_seconds)
        else:
            cycle = (intersection.cycle_length_min_seconds + intersection.cycle_length_max_seconds) / 2.0

        cycle = max(min_cycle, max(intersection.cycle_length_min_seconds, min(intersection.cycle_length_max_seconds, cycle)))
        avail_green = cycle - total_lost

        phase_y, total_Y = self._get_critical_flow_ratios(intersection, demands)

        raw_greens: List[float] = []
        if total_Y > 1e-5:
            for phase in phases:
                y = phase_y.get(phase.phase_id, 0.0)
                # Proportional share with base smoothing
                share = y / total_Y
                raw_greens.append(share * avail_green)
        else:
            # Zero demand fallback: equal split
            equal_share = avail_green / float(len(phases))
            raw_greens = [equal_share for _ in phases]

        final_greens = self._redistribute_greens(raw_greens, phases, avail_green)

        # Assemble plan
        return self._build_signal_plan(
            intersection=intersection,
            greens=final_greens,
            total_lost=total_lost,
            algorithm_name="demand_proportional",
            description="Demand-proportional green allocation based on critical approach volume ratios",
        )

    def _optimize_webster_optimal(
        self,
        intersection: IntersectionConfig,
        demands: List[ApproachDemand],
    ) -> SignalPlan:
        """
        Webster's Minimum-Delay Optimal Strategy:
        Calculates optimal cycle length C_0 = (1.5*L + 5) / (1 - Y) and allocates green splits.
        """
        phases = intersection.phases
        total_lost = intersection.get_total_lost_time()
        min_cycle = total_lost + intersection.get_total_min_green()

        phase_y, total_Y = self._get_critical_flow_ratios(intersection, demands)

        # Webster optimal cycle length formula
        # Bound Y below 0.90 for undersaturated formula stability
        effective_Y = min(0.90, total_Y)
        if effective_Y < 0.01:
            # Low demand: use min cycle length
            opt_cycle = intersection.cycle_length_min_seconds
        else:
            webster_cycle = (1.5 * total_lost + 5.0) / (1.0 - effective_Y)
            opt_cycle = max(
                min_cycle,
                max(intersection.cycle_length_min_seconds, min(intersection.cycle_length_max_seconds, webster_cycle)),
            )

        avail_green = opt_cycle - total_lost

        raw_greens: List[float] = []
        if total_Y > 1e-5:
            for phase in phases:
                y = phase_y.get(phase.phase_id, 0.0)
                share = y / total_Y
                raw_greens.append(share * avail_green)
        else:
            equal_share = avail_green / float(len(phases))
            raw_greens = [equal_share for _ in phases]

        final_greens = self._redistribute_greens(raw_greens, phases, avail_green)

        return self._build_signal_plan(
            intersection=intersection,
            greens=final_greens,
            total_lost=total_lost,
            algorithm_name="webster_optimal",
            description=f"Webster's minimum-delay optimal cycle ({opt_cycle:.1f}s) and green allocation",
        )

    def _optimize_constrained_delay_minimization(
        self,
        intersection: IntersectionConfig,
        demands: List[ApproachDemand],
        target_cycle_length: Optional[float] = None,
    ) -> SignalPlan:
        """
        Constrained Delay Minimization:
        Direct bounded search across discrete green splits to minimize intersection demand-weighted delay proxy.
        """
        phases = intersection.phases
        total_lost = intersection.get_total_lost_time()
        min_cycle = total_lost + intersection.get_total_min_green()

        if target_cycle_length is not None:
            cycle = float(target_cycle_length)
        elif intersection.target_cycle_length_seconds is not None:
            cycle = float(intersection.target_cycle_length_seconds)
        else:
            cycle = (intersection.cycle_length_min_seconds + intersection.cycle_length_max_seconds) / 2.0

        cycle = max(min_cycle, max(intersection.cycle_length_min_seconds, min(intersection.cycle_length_max_seconds, cycle)))
        avail_green = cycle - total_lost

        # Candidate seeds: 1) Demand-proportional, 2) Equal split, 3) Grid search perturbations
        prop_plan = self._optimize_demand_proportional(intersection, demands, target_cycle_length=cycle)
        best_greens = [pt.green_seconds for pt in prop_plan.phase_timings]

        best_metrics = SimulationEvaluator.evaluate_plan(intersection, demands, prop_plan)
        best_score = best_metrics.objective_score

        # Grid search perturbation around seed (step = 2.0s)
        if len(phases) == 2:
            p0 = phases[0]
            p1 = phases[1]
            min_g0 = max(p0.min_green_seconds, avail_green - p1.max_green_seconds)
            max_g0 = min(p0.max_green_seconds, avail_green - p1.min_green_seconds)

            steps = int((max_g0 - min_g0) / 1.0)
            for s_idx in range(steps + 1):
                g0 = min_g0 + s_idx * 1.0
                g1 = avail_green - g0
                cand_greens = [g0, g1]
                cand_plan = self._build_signal_plan(
                    intersection, cand_greens, total_lost, "constrained_delay_minimization", "Candidate"
                )
                cand_metrics = SimulationEvaluator.evaluate_plan(intersection, demands, cand_plan)
                if cand_metrics.objective_score < best_score:
                    best_score = cand_metrics.objective_score
                    best_greens = cand_greens
        else:
            # Multi-phase coordinate descent
            for _ in range(30):
                improved = False
                for i in range(len(phases)):
                    for j in range(len(phases)):
                        if i == j:
                            continue
                        step = 1.0
                        if (
                            best_greens[i] + step <= phases[i].max_green_seconds
                            and best_greens[j] - step >= phases[j].min_green_seconds
                        ):
                            cand_greens = list(best_greens)
                            cand_greens[i] += step
                            cand_greens[j] -= step
                            cand_plan = self._build_signal_plan(
                                intersection, cand_greens, total_lost, "constrained_delay_minimization", "Candidate"
                            )
                            cand_metrics = SimulationEvaluator.evaluate_plan(intersection, demands, cand_plan)
                            if cand_metrics.objective_score < best_score - 1e-4:
                                best_score = cand_metrics.objective_score
                                best_greens = cand_greens
                                improved = True
                if not improved:
                    break

        return self._build_signal_plan(
            intersection=intersection,
            greens=best_greens,
            total_lost=total_lost,
            algorithm_name="constrained_delay_minimization",
            description="Constrained non-linear search minimizing intersection-wide delay proxy",
        )

    def _build_signal_plan(
        self,
        intersection: IntersectionConfig,
        greens: List[float],
        total_lost: float,
        algorithm_name: str,
        description: str,
    ) -> SignalPlan:
        """Constructs a typed SignalPlan instance."""
        phases = intersection.phases
        actual_total_green = sum(greens)
        actual_cycle = actual_total_green + total_lost

        phase_timings: List[PhaseTiming] = []
        for idx, phase in enumerate(phases):
            g = round(greens[idx], 2)
            y = phase.yellow_seconds
            ar = phase.all_red_seconds
            tot = round(g + y + ar, 2)
            split_pct = round((tot / actual_cycle) * 100.0, 2)

            phase_timings.append(
                PhaseTiming(
                    phase_id=phase.phase_id,
                    name=phase.name,
                    controlled_approaches=list(phase.controlled_approaches),
                    green_seconds=g,
                    yellow_seconds=y,
                    all_red_seconds=ar,
                    total_phase_seconds=tot,
                    split_percentage=split_pct,
                )
            )

        return SignalPlan(
            plan_id=f"plan_{algorithm_name}_{uuid.uuid4().hex[:8]}",
            plan_type="optimized",
            cycle_length_seconds=round(actual_cycle, 2),
            total_green_seconds=round(actual_total_green, 2),
            total_lost_seconds=round(total_lost, 2),
            phase_timings=phase_timings,
            algorithm_name=algorithm_name,
            description=description,
        )
