"""
Mathematical Objective Functions and Simulation Evaluation Engine.
Phase 12: Traffic Signal Optimization Simulation.

Computes mathematically grounded performance proxies:
- Webster's delay proxy (uniform + random delay with HCM oversaturation transition)
- Queue length proxy
- Throughput capacity proxy
- Intersection-wide demand-weighted delay and Level of Service (LOS) proxy
- Before/After comparison deltas and honest improvement calculations.
"""
import math
from typing import Dict, List, Tuple

from app.services.simulation.models import (
    ApproachComparison,
    ApproachConfig,
    ApproachDemand,
    ApproachPerformance,
    IntersectionConfig,
    LevelOfService,
    PhaseComparison,
    SignalPlan,
    SimulationMetrics,
    compute_los,
)


class SimulationEvaluator:
    """
    Evaluates a SignalPlan against an Intersection's traffic demands using
    classical Webster delay models and Highway Capacity Manual (HCM) formulations.
    """

    @staticmethod
    def compute_approach_performance(
        approach: ApproachConfig,
        demand: ApproachDemand,
        allocated_green: float,
        cycle_length: float,
    ) -> ApproachPerformance:
        """
        Calculates performance proxies for a single approach given allocated green time.
        """
        q = max(0.0, float(demand.vehicle_flow_rate_vph))  # Arrival flow rate (veh/hr)
        s = approach.get_total_saturation_flow()  # Total saturation flow (veh/hr)
        g = max(0.1, float(allocated_green))  # Effective green (seconds)
        C = max(1.0, float(cycle_length))  # Cycle length (seconds)

        green_ratio = min(1.0, g / C)  # lambda = g / C
        capacity = max(1.0, s * green_ratio)  # c = s * (g / C) in veh/hr
        degree_of_saturation = q / capacity  # x = q / c

        # Calculate Webster's Delay Proxy
        delay = SimulationEvaluator._calculate_webster_delay(
            q=q,
            s=s,
            g=g,
            C=C,
            green_ratio=green_ratio,
            capacity=capacity,
            x=degree_of_saturation,
        )

        # Calculate Queue Length Proxy
        queue = SimulationEvaluator._calculate_queue_proxy(
            q=q,
            g=g,
            C=C,
            capacity=capacity,
            x=degree_of_saturation,
        )

        los = compute_los(delay)

        return ApproachPerformance(
            approach_id=approach.approach_id,
            name=approach.name,
            demand_flow_rate_vph=round(q, 1),
            allocated_green_seconds=round(g, 1),
            cycle_length_seconds=round(C, 1),
            green_ratio=round(green_ratio, 3),
            capacity_vph=round(capacity, 1),
            degree_of_saturation_x=round(degree_of_saturation, 3),
            estimated_delay_seconds=round(delay, 2),
            estimated_queue_vehicles=round(queue, 2),
            los_grade=los,
        )

    @staticmethod
    def _calculate_webster_delay(
        q: float,
        s: float,
        g: float,
        C: float,
        green_ratio: float,
        capacity: float,
        x: float,
    ) -> float:
        """
        Computes Webster's Delay Proxy (sec/veh).
        Uses Webster's uniform + random delay formula with standard HCM transition for oversaturation.
        """
        if q <= 0.0:
            return 0.0

        red_ratio = max(0.0, 1.0 - green_ratio)

        if x <= 0.90:
            # Standard Webster Formulation
            # d1 = Uniform delay = C * (1 - lambda)^2 / (2 * (1 - lambda * x))
            denom1 = max(0.01, 2.0 * (1.0 - green_ratio * x))
            d1 = (C * (red_ratio ** 2)) / denom1

            # d2 = Random delay = x^2 / (2 * q_sec * (1 - x))
            q_sec = q / 3600.0
            denom2 = max(0.001, 2.0 * q_sec * (1.0 - x))
            d2 = (x ** 2) / denom2

            # d3 = Webster empirical correction term = 0.65 * (C / q^2)^(1/3) * x^(2 + 5*lambda)
            try:
                term = C / max(1.0, q ** 2)
                d3 = 0.65 * (term ** (1.0 / 3.0)) * (x ** (2.0 + 5.0 * green_ratio))
            except Exception:
                d3 = 0.0

            total_delay = max(1.0, d1 + d2 - d3)
        else:
            # Near-saturated or Oversaturated Flow (HCM formulation with T = 0.25h = 15 min analysis horizon)
            # Uniform delay at x=0.90 cap
            d1 = (C * (red_ratio ** 2)) / max(0.01, 2.0 * (1.0 - green_ratio * 0.90))

            T = 0.25  # 15 minutes (hours)
            k = 0.5  # Fixed-time controller factor
            I = 1.0  # Upstream filtering adjustment

            term_sqrt = (x - 1.0) ** 2 + ((8.0 * k * I * x) / max(1.0, capacity * T))
            d2_incremental = 900.0 * T * ((x - 1.0) + math.sqrt(max(0.0, term_sqrt)))

            total_delay = max(d1 + 5.0, d1 + d2_incremental)

        return min(300.0, total_delay)  # Cap delay proxy at 300s to avoid numerical explosion

    @staticmethod
    def _calculate_queue_proxy(
        q: float,
        g: float,
        C: float,
        capacity: float,
        x: float,
    ) -> float:
        """
        Computes maximum back-of-queue proxy per cycle (vehicles).
        """
        if q <= 0.0:
            return 0.0

        red_seconds = max(0.0, C - g)
        uniform_queue = (q * red_seconds) / 3600.0

        if x <= 0.90:
            random_overflow = (x ** 2) / max(0.01, 2.0 * (1.0 - x))
        else:
            # Overflow during 15-minute peak
            random_overflow = max(0.0, (q - capacity) * 0.25) + 3.0 * x

        return max(0.0, uniform_queue + random_overflow)

    @classmethod
    def evaluate_plan(
        cls,
        intersection: IntersectionConfig,
        demands: List[ApproachDemand],
        signal_plan: SignalPlan,
    ) -> SimulationMetrics:
        """
        Evaluates an entire SignalPlan across all approaches and computes intersection-wide KPIs.
        """
        # Map approach_id to allocated green seconds in signal_plan
        demand_map: Dict[str, ApproachDemand] = {d.approach_id: d for d in demands}
        approach_green_map: Dict[str, float] = {}

        for pt in signal_plan.phase_timings:
            for app_id in pt.controlled_approaches:
                approach_green_map[app_id] = pt.green_seconds

        performances: List[ApproachPerformance] = []
        total_demand_weighted_delay = 0.0
        total_demand_volume = 0.0
        total_queue = 0.0
        total_throughput = 0.0
        max_v_c = 0.0

        for approach in intersection.approaches:
            demand = demand_map.get(
                approach.approach_id,
                ApproachDemand(approach_id=approach.approach_id, vehicle_flow_rate_vph=0.0),
            )
            green = approach_green_map.get(approach.approach_id, 10.0)

            perf = cls.compute_approach_performance(
                approach=approach,
                demand=demand,
                allocated_green=green,
                cycle_length=signal_plan.cycle_length_seconds,
            )
            performances.append(perf)

            q = perf.demand_flow_rate_vph
            total_demand_weighted_delay += q * perf.estimated_delay_seconds
            total_demand_volume += q
            total_queue += perf.estimated_queue_vehicles
            total_throughput += min(q, perf.capacity_vph)
            max_v_c = max(max_v_c, perf.degree_of_saturation_x)

        if total_demand_volume > 0:
            avg_delay = total_demand_weighted_delay / total_demand_volume
        else:
            avg_delay = sum(p.estimated_delay_seconds for p in performances) / max(1, len(performances))

        intersection_los = compute_los(avg_delay)
        objective_score = avg_delay + 0.25 * total_queue

        return SimulationMetrics(
            cycle_length_seconds=signal_plan.cycle_length_seconds,
            total_green_seconds=signal_plan.total_green_seconds,
            average_delay_seconds_per_vehicle=round(avg_delay, 2),
            total_queue_vehicles=round(total_queue, 2),
            throughput_capacity_vph=round(total_throughput, 1),
            critical_v_c_ratio=round(max_v_c, 3),
            intersection_los=intersection_los,
            objective_score=round(objective_score, 2),
            approach_performances=performances,
        )

    @staticmethod
    def compare_plans(
        intersection: IntersectionConfig,
        demands: List[ApproachDemand],
        baseline_plan: SignalPlan,
        optimized_plan: SignalPlan,
        baseline_metrics: SimulationMetrics,
        optimized_metrics: SimulationMetrics,
    ) -> Tuple[List[PhaseComparison], List[ApproachComparison], float, float, float, float]:
        """
        Generates granular phase and approach comparisons, deltas, and honest improvement percentages.
        """
        # Phase comparisons
        phase_comps: List[PhaseComparison] = []
        base_phase_map = {p.phase_id: p for p in baseline_plan.phase_timings}
        opt_phase_map = {p.phase_id: p for p in optimized_plan.phase_timings}

        for phase_cfg in intersection.phases:
            p_id = phase_cfg.phase_id
            bp = base_phase_map.get(p_id)
            op = opt_phase_map.get(p_id)

            bg = bp.green_seconds if bp else 0.0
            og = op.green_seconds if op else 0.0
            bs = bp.split_percentage if bp else 0.0
            os = op.split_percentage if op else 0.0

            phase_comps.append(
                PhaseComparison(
                    phase_id=p_id,
                    name=phase_cfg.name,
                    controlled_approaches=list(phase_cfg.controlled_approaches),
                    baseline_green_seconds=round(bg, 1),
                    optimized_green_seconds=round(og, 1),
                    green_delta_seconds=round(og - bg, 1),
                    baseline_split_pct=round(bs, 1),
                    optimized_split_pct=round(os, 1),
                    split_delta_pct=round(os - bs, 1),
                )
            )

        # Approach comparisons
        app_comps: List[ApproachComparison] = []
        base_app_map = {p.approach_id: p for p in baseline_metrics.approach_performances}
        opt_app_map = {p.approach_id: p for p in optimized_metrics.approach_performances}

        for app_cfg in intersection.approaches:
            a_id = app_cfg.approach_id
            bp = base_app_map.get(a_id)
            op = opt_app_map.get(a_id)

            demand_val = bp.demand_flow_rate_vph if bp else 0.0
            bg = bp.allocated_green_seconds if bp else 0.0
            og = op.allocated_green_seconds if op else 0.0
            bd = bp.estimated_delay_seconds if bp else 0.0
            od = op.estimated_delay_seconds if op else 0.0
            bq = bp.estimated_queue_vehicles if bp else 0.0
            oq = op.estimated_queue_vehicles if op else 0.0
            blos = bp.los_grade if bp else LevelOfService.LOS_A
            olos = op.los_grade if op else LevelOfService.LOS_A

            delay_diff = od - bd
            delay_red_pct = 0.0
            if bd > 1e-4:
                delay_red_pct = ((bd - od) / bd) * 100.0

            app_comps.append(
                ApproachComparison(
                    approach_id=a_id,
                    name=app_cfg.name,
                    demand_vph=round(demand_val, 1),
                    baseline_green_seconds=round(bg, 1),
                    optimized_green_seconds=round(og, 1),
                    baseline_delay_seconds=round(bd, 2),
                    optimized_delay_seconds=round(od, 2),
                    delay_delta_seconds=round(delay_diff, 2),
                    delay_reduction_pct=round(delay_red_pct, 1),
                    baseline_queue_vehicles=round(bq, 2),
                    optimized_queue_vehicles=round(oq, 2),
                    queue_delta_vehicles=round(oq - bq, 2),
                    baseline_los=blos,
                    optimized_los=olos,
                )
            )

        # Overall improvement percentages
        base_delay = baseline_metrics.average_delay_seconds_per_vehicle
        opt_delay = optimized_metrics.average_delay_seconds_per_vehicle
        delay_red_overall = 0.0
        if base_delay > 1e-4:
            delay_red_overall = max(-100.0, min(100.0, ((base_delay - opt_delay) / base_delay) * 100.0))

        base_queue = baseline_metrics.total_queue_vehicles
        opt_queue = optimized_metrics.total_queue_vehicles
        queue_red_overall = 0.0
        if base_queue > 1e-4:
            queue_red_overall = max(-100.0, min(100.0, ((base_queue - opt_queue) / base_queue) * 100.0))

        base_thru = baseline_metrics.throughput_capacity_vph
        opt_thru = optimized_metrics.throughput_capacity_vph
        thru_inc_overall = 0.0
        if base_thru > 1e-4:
            thru_inc_overall = max(-100.0, min(100.0, ((opt_thru - base_thru) / base_thru) * 100.0))

        base_score = baseline_metrics.objective_score
        opt_score = optimized_metrics.objective_score
        obj_imp_overall = 0.0
        if base_score > 1e-4:
            obj_imp_overall = max(-100.0, min(100.0, ((base_score - opt_score) / base_score) * 100.0))

        return (
            phase_comps,
            app_comps,
            round(delay_red_overall, 2),
            round(queue_red_overall, 2),
            round(thru_inc_overall, 2),
            round(obj_imp_overall, 2),
        )
