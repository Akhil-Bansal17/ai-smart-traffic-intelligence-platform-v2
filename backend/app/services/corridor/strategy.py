"""
Signal Priority Strategy and Safety Constraints Engine.
Phase 13: Emergency Corridor Simulation.

Implements explainable signal priority algorithms:
- Estimated Arrival Time (ETA) calculation across corridor nodes
- Queue clearance lead-time determination
- Green Extension vs Early Green phase timing adjustments
- Strict safety constraints: min green, yellow/all-red clearance, conflicting phase protection, max green cap
- Phase-safe recovery timing calculations
- Cross-street delay impact evaluation using Webster/HCM formulations.
"""
import math
import uuid
from typing import Dict, List, Optional, Tuple

from app.services.corridor.models import (
    CorridorConfig,
    CorridorNodeConfig,
    EmergencyVehicleConfig,
    NodeSimulationTimeline,
    PriorityStrategyType,
    PriorityWindow,
    RecoveryStrategyType,
    SignalPriorityAction,
)
from app.services.simulation.baseline import BaselineSignalStrategy
from app.services.simulation.models import (
    ApproachConfig,
    ApproachDemand,
    ApproachPerformance,
    IntersectionConfig,
    PhaseTiming,
    SignalPhaseConfig,
    SignalPlan,
)
from app.services.simulation.objective import SimulationEvaluator


class SignalPriorityStrategyEngine:
    """
    Coordinates multi-intersection corridor progression and calculates safe,
    explainable signal priority timing plans and recovery transitions.
    """

    def __init__(self):
        self.baseline_strategy = BaselineSignalStrategy()

    def compute_travel_time_seconds(
        self,
        distance_m: float,
        speed_kmh: float,
    ) -> float:
        """Calculates free-flow travel time between two nodes."""
        if distance_m <= 0.0 or speed_kmh <= 0.0:
            return 0.0
        speed_mps = speed_kmh / 3.6
        return distance_m / speed_mps

    def compute_queue_clearance_lead_time(
        self,
        node: CorridorNodeConfig,
        corridor_approach: ApproachConfig,
        corridor_demand: ApproachDemand,
        baseline_plan: SignalPlan,
    ) -> Tuple[float, float]:
        """
        Calculates standing queue and required green lead time to discharge
        standing vehicles ahead of the arriving emergency vehicle.

        Returns (queue_vehicles, lead_time_seconds).
        """
        # Calculate queue length under baseline plan
        eval_perf = SimulationEvaluator.compute_approach_performance(
            approach=corridor_approach,
            demand=corridor_demand,
            allocated_green=self._get_phase_green(baseline_plan, node.corridor_phase_id),
            cycle_length=baseline_plan.cycle_length_seconds,
        )
        queue_veh = max(0.0, eval_perf.estimated_queue_vehicles)

        # Saturation discharge headway: ~2.0s per vehicle per lane (at 1800 veh/hr/lane)
        lanes = max(1, corridor_approach.lanes)
        discharge_headway = (3600.0 / corridor_approach.saturation_flow_rate_per_lane) / float(lanes)

        # Lead time: time to clear standing queue plus safety buffer (minimum 3.0s, capped at 25.0s)
        lead_time = max(3.0, min(25.0, queue_veh * discharge_headway + 2.0))
        return round(queue_veh, 2), round(lead_time, 1)

    def calculate_priority_window(
        self,
        node: CorridorNodeConfig,
        arrival_time_sec: float,
        corridor_approach: ApproachConfig,
        corridor_demand: ApproachDemand,
        baseline_plan: SignalPlan,
        strategy_type: PriorityStrategyType,
    ) -> PriorityWindow:
        """
        Computes the priority activation window [T_start, T_end] for an intersection node.
        """
        queue_veh, lead_time = self.compute_queue_clearance_lead_time(
            node=node,
            corridor_approach=corridor_approach,
            corridor_demand=corridor_demand,
            baseline_plan=baseline_plan,
        )
        clearance_window = 5.0  # seconds buffer after emergency vehicle reaches intersection

        t_start = max(0.0, arrival_time_sec - lead_time)
        t_end = arrival_time_sec + clearance_window

        # Determine signal cycle state at arrival
        cycle_len = baseline_plan.cycle_length_seconds
        time_in_cycle = arrival_time_sec % cycle_len

        # Get corridor phase baseline start and end in cycle
        corr_pt = baseline_plan.get_phase_timing(node.corridor_phase_id)
        phase_start, phase_end = self._get_phase_cycle_window(baseline_plan, node.corridor_phase_id)

        corridor_phase_cfg = node.get_corridor_phase()
        max_green_cap = min(120.0, (corridor_phase_cfg.max_green_seconds if corridor_phase_cfg else 65.0) * 1.4)

        if phase_start <= time_in_cycle < phase_end:
            # Vehicle arrives during corridor green -> Green Extension
            remaining_green = phase_end - time_in_cycle
            extension_needed = max(0.0, clearance_window - remaining_green)
            action = SignalPriorityAction.GREEN_EXTENSION
            green_ext = min(max_green_cap - (corr_pt.green_seconds if corr_pt else 30.0), extension_needed)
            early_grn = 0.0
        else:
            # Vehicle arrives during corridor red -> Early Green / Truncation
            action = SignalPriorityAction.EARLY_GREEN
            green_ext = 0.0
            time_until_green = (phase_start - time_in_cycle) % cycle_len
            early_grn = max(0.0, time_until_green)

        recovery_duration = cycle_len * 1.5  # Approximate recovery duration (1-2 cycles)

        return PriorityWindow(
            node_id=node.node_id,
            estimated_arrival_seconds=round(arrival_time_sec, 2),
            queue_clearance_lead_time_seconds=lead_time,
            clearance_window_seconds=clearance_window,
            priority_start_seconds=round(t_start, 2),
            priority_end_seconds=round(t_end, 2),
            action_applied=action,
            green_extension_seconds=round(green_ext, 1),
            early_green_seconds=round(early_grn, 1),
            recovery_duration_seconds=round(recovery_duration, 1),
            max_priority_green_cap_seconds=round(max_green_cap, 1),
        )

    def generate_priority_signal_plan(
        self,
        node: CorridorNodeConfig,
        baseline_plan: SignalPlan,
        priority_window: PriorityWindow,
    ) -> SignalPlan:
        """
        Generates a valid, safety-constrained SignalPlan for the priority cycle.

        Safety constraints enforced:
        1. Minimum green (g_min) for all conflicting phases is strictly respected.
        2. Yellow clearance and all-red clearance intervals are NEVER reduced.
        3. Maximum green cap is not exceeded.
        4. Conflicting movements are strictly protected (never green simultaneously).
        """
        phases = node.intersection.phases
        corridor_phase_id = node.corridor_phase_id

        # Copy baseline timings
        new_timings: List[PhaseTiming] = []
        cycle_len = baseline_plan.cycle_length_seconds
        total_lost = node.intersection.get_total_lost_time()

        # Calculate modified green times
        green_allocations: Dict[str, float] = {}
        for pt in baseline_plan.phase_timings:
            green_allocations[pt.phase_id] = pt.green_seconds

        # Determine priority boost for corridor phase
        boost = 0.0
        if priority_window.action_applied == SignalPriorityAction.GREEN_EXTENSION:
            boost = max(4.0, priority_window.green_extension_seconds + 5.0)
        elif priority_window.action_applied == SignalPriorityAction.EARLY_GREEN:
            boost = max(6.0, min(20.0, priority_window.early_green_seconds))
        else:
            boost = 5.0

        corridor_phase_cfg = node.get_corridor_phase()
        max_green_allowed = priority_window.max_priority_green_cap_seconds
        curr_corr_green = green_allocations.get(corridor_phase_id, 30.0)
        target_corr_green = min(max_green_allowed, curr_corr_green + boost)
        actual_boost = target_corr_green - curr_corr_green

        # Truncate green from conflicting phases, respecting min_green_seconds
        conflicting_phases = [p for p in phases if p.phase_id != corridor_phase_id]
        if conflicting_phases and actual_boost > 0.0:
            boost_per_conflict = actual_boost / float(len(conflicting_phases))
            total_deducted = 0.0

            for cp in conflicting_phases:
                cur_g = green_allocations.get(cp.phase_id, 20.0)
                safe_min_g = cp.min_green_seconds
                max_deductible = max(0.0, cur_g - safe_min_g)
                deduct = min(max_deductible, boost_per_conflict)
                green_allocations[cp.phase_id] = cur_g - deduct
                total_deducted += deduct

            green_allocations[corridor_phase_id] = curr_corr_green + total_deducted
        else:
            green_allocations[corridor_phase_id] = curr_corr_green

        # Build modified phase timings
        actual_total_green = sum(green_allocations.values())
        actual_cycle = actual_total_green + total_lost

        for phase in phases:
            g = round(green_allocations[phase.phase_id], 2)
            y = phase.yellow_seconds
            ar = phase.all_red_seconds
            tot = round(g + y + ar, 2)
            split_pct = round((tot / actual_cycle) * 100.0, 2)

            new_timings.append(
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
            plan_id=f"plan_prio_{uuid.uuid4().hex[:8]}",
            plan_type="priority",
            cycle_length_seconds=round(actual_cycle, 2),
            total_green_seconds=round(actual_total_green, 2),
            total_lost_seconds=round(total_lost, 2),
            phase_timings=new_timings,
            algorithm_name=f"emergency_priority_{priority_window.action_applied.value}",
            description=f"Emergency signal priority plan ({priority_window.action_applied.value}) with safety clearance constraints",
        )

    def generate_recovery_signal_plan(
        self,
        node: CorridorNodeConfig,
        baseline_plan: SignalPlan,
        priority_plan: SignalPlan,
        recovery_strategy: RecoveryStrategyType,
    ) -> SignalPlan:
        """
        Generates a phase-safe Recovery SignalPlan to compensate starved cross-street phases
        and resynchronize intersection timing with the baseline network cycle.
        """
        if recovery_strategy == RecoveryStrategyType.IMMEDIATE_RESUME:
            return baseline_plan

        # Smooth compensation: Give back truncated green to conflicting phases
        phases = node.intersection.phases
        corridor_phase_id = node.corridor_phase_id
        total_lost = node.intersection.get_total_lost_time()

        base_corr_pt = baseline_plan.get_phase_timing(corridor_phase_id)
        prio_corr_pt = priority_plan.get_phase_timing(corridor_phase_id)

        corridor_excess_green = 0.0
        if base_corr_pt and prio_corr_pt:
            corridor_excess_green = max(0.0, prio_corr_pt.green_seconds - base_corr_pt.green_seconds)

        green_allocations: Dict[str, float] = {}
        for pt in baseline_plan.phase_timings:
            green_allocations[pt.phase_id] = pt.green_seconds

        conflicting_phases = [p for p in phases if p.phase_id != corridor_phase_id]
        if conflicting_phases and corridor_excess_green > 0.0:
            # Compensate conflicting phases
            comp_per_conflict = (corridor_excess_green * 0.75) / float(len(conflicting_phases))
            corridor_reduction = 0.0

            for cp in conflicting_phases:
                cur_g = green_allocations.get(cp.phase_id, 20.0)
                max_g = cp.max_green_seconds
                comp = min(max_g - cur_g, comp_per_conflict)
                green_allocations[cp.phase_id] = cur_g + comp
                corridor_reduction += comp

            cur_corr_g = green_allocations[corridor_phase_id]
            corr_min_g = (node.get_corridor_phase().min_green_seconds if node.get_corridor_phase() else 10.0)
            green_allocations[corridor_phase_id] = max(corr_min_g, cur_corr_g - corridor_reduction)

        # Build recovery phase timings
        new_timings: List[PhaseTiming] = []
        actual_total_green = sum(green_allocations.values())
        actual_cycle = actual_total_green + total_lost

        for phase in phases:
            g = round(green_allocations[phase.phase_id], 2)
            y = phase.yellow_seconds
            ar = phase.all_red_seconds
            tot = round(g + y + ar, 2)
            split_pct = round((tot / actual_cycle) * 100.0, 2)

            new_timings.append(
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
            plan_id=f"plan_recovery_{uuid.uuid4().hex[:8]}",
            plan_type="recovery",
            cycle_length_seconds=round(actual_cycle, 2),
            total_green_seconds=round(actual_total_green, 2),
            total_lost_seconds=round(total_lost, 2),
            phase_timings=new_timings,
            algorithm_name="phase_safe_recovery",
            description="Phase-safe recovery plan compensating cross-street phases following priority clearance",
        )

    # --------------------------------------------------------------------------
    # Helper Methods
    # --------------------------------------------------------------------------
    def _get_phase_green(self, plan: SignalPlan, phase_id: str) -> float:
        pt = plan.get_phase_timing(phase_id)
        return pt.green_seconds if pt else 25.0

    def _get_phase_cycle_window(self, plan: SignalPlan, phase_id: str) -> Tuple[float, float]:
        """Returns (start_sec, end_sec) within cycle for a given phase."""
        accum = 0.0
        for pt in plan.phase_timings:
            if pt.phase_id == phase_id:
                return (accum, accum + pt.green_seconds)
            accum += pt.total_phase_seconds
        return (0.0, 30.0)
