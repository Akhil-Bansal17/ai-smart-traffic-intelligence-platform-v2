"""
Deterministic Baseline Signal Plan Generator.
Phase 12: Traffic Signal Optimization Simulation.

Implements standard un-actuated fixed-time signal timing baseline.
Allocates available green time equally across configured phases, respecting clearance and min/max safety limits.
"""
import uuid
from typing import List, Optional

from app.services.simulation.models import (
    IntersectionConfig,
    PhaseTiming,
    SignalPhaseConfig,
    SignalPlan,
)


class BaselineSignalStrategy:
    """
    Generates a deterministic, fixed-time signal plan where available green time
    is distributed equally across all phases.

    Mathematical definition:
    1. Total lost clearance time L = sum(yellow_i + all_red_i) for all phases i in 1..N.
    2. Effective cycle length C is set to intersection target_cycle_length (or midpoint of min/max bounds).
    3. Total available green time G_avail = C - L.
    4. Base green allocation per phase: g_i = G_avail / N.
    5. Bounds enforcement: g_i is clamped to [min_green_i, max_green_i].
    6. Remainder redistribution ensures sum(g_i) == G_avail exactly.
    """

    def generate_baseline_plan(
        self,
        intersection: IntersectionConfig,
        target_cycle_length: Optional[float] = None,
    ) -> SignalPlan:
        """
        Creates the deterministic baseline SignalPlan for the given intersection.
        """
        phases = intersection.phases
        if not phases:
            raise ValueError("Intersection has no signal phases defined.")

        num_phases = len(phases)
        total_lost = intersection.get_total_lost_time()
        min_required_cycle = total_lost + intersection.get_total_min_green()

        # Determine target cycle length
        if target_cycle_length is not None:
            cycle_length = float(target_cycle_length)
        elif intersection.target_cycle_length_seconds is not None:
            cycle_length = float(intersection.target_cycle_length_seconds)
        else:
            cycle_length = (intersection.cycle_length_min_seconds + intersection.cycle_length_max_seconds) / 2.0

        # Clamp cycle length to configured intersection bounds and minimum feasibility
        cycle_length = max(
            min_required_cycle,
            max(intersection.cycle_length_min_seconds, min(intersection.cycle_length_max_seconds, cycle_length)),
        )

        total_available_green = cycle_length - total_lost
        if total_available_green < sum(p.min_green_seconds for p in phases):
            # If available green is lower than sum of min greens, cycle length must expand to accommodate safety minima
            cycle_length = total_lost + sum(p.min_green_seconds for p in phases)
            total_available_green = cycle_length - total_lost

        # Initial equal green allocation
        equal_green = total_available_green / float(num_phases)
        green_allocations = [equal_green for _ in phases]

        # Clamp each phase green to [min_green, max_green]
        for idx, phase in enumerate(phases):
            green_allocations[idx] = max(
                phase.min_green_seconds,
                min(phase.max_green_seconds, green_allocations[idx]),
            )

        # Redistribute residual difference to ensure exact green sum
        current_sum = sum(green_allocations)
        diff = total_available_green - current_sum

        if abs(diff) > 1e-4:
            # Distribute diff among phases that have slack
            for _ in range(50):  # Convergence loop
                if abs(diff) <= 1e-4:
                    break
                eligible_indices = []
                for idx, phase in enumerate(phases):
                    if diff > 0 and green_allocations[idx] < phase.max_green_seconds - 1e-4:
                        eligible_indices.append(idx)
                    elif diff < 0 and green_allocations[idx] > phase.min_green_seconds + 1e-4:
                        eligible_indices.append(idx)

                if not eligible_indices:
                    break

                adjustment_per_phase = diff / float(len(eligible_indices))
                for idx in eligible_indices:
                    phase = phases[idx]
                    old_val = green_allocations[idx]
                    new_val = max(
                        phase.min_green_seconds,
                        min(phase.max_green_seconds, old_val + adjustment_per_phase),
                    )
                    green_allocations[idx] = new_val

                current_sum = sum(green_allocations)
                diff = total_available_green - current_sum

        # Build phase timings
        phase_timings: List[PhaseTiming] = []
        actual_total_green = sum(green_allocations)
        actual_cycle = actual_total_green + total_lost

        for idx, phase in enumerate(phases):
            g = round(green_allocations[idx], 2)
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
            plan_id=f"plan_baseline_{uuid.uuid4().hex[:8]}",
            plan_type="baseline",
            cycle_length_seconds=round(actual_cycle, 2),
            total_green_seconds=round(actual_total_green, 2),
            total_lost_seconds=round(total_lost, 2),
            phase_timings=phase_timings,
            algorithm_name="fixed_equal_baseline",
            description="Deterministic un-actuated fixed-time baseline with equal green distribution",
        )
