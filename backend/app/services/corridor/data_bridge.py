"""
Corridor Traffic Data Bridge and Provenance Classifier.
Phase 13: Emergency Corridor Simulation.

Bridges recorded AnalysisSession metrics from database to corridor intersection nodes,
maintaining the strict 4-way provenance hierarchy:
  1. real_database_metrics
  2. synthetic_pipeline_metrics
  3. simulation_configured
  4. synthetic_fixture
"""
from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.analysis import AnalysisSession, TrafficMetricsRecord
from app.models.video import Video
from app.services.corridor.models import CorridorNodeConfig
from app.services.simulation.data_bridge import TrafficDataBridge
from app.services.simulation.models import ApproachDemand, IntersectionConfig


class CorridorDataBridge:
    """
    Connects database analysis records to corridor nodes, ensuring honest data provenance tagging.
    """

    @classmethod
    def populate_node_demands_from_session(
        cls,
        db: Session,
        session_id: str,
        node: CorridorNodeConfig,
    ) -> Tuple[List[ApproachDemand], str, List[str]]:
        """
        Extracts demand from an AnalysisSession for a specific corridor node intersection.
        """
        demands, provenance, notes = TrafficDataBridge.extract_demand_from_session(
            db=db,
            session_id=session_id,
            intersection=node.intersection,
        )
        node.demands = demands
        return demands, provenance, notes
