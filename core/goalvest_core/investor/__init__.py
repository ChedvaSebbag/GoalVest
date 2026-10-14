"""פרופיל משקיע ושאלון סיכון."""

from goalvest_core.investor.profile import InvestorProfile
from goalvest_core.investor.scoring import LABELS, Assessment, evaluate

__all__ = ["LABELS", "Assessment", "InvestorProfile", "evaluate"]
