from typing import Annotated
from langgraph.graph.message import add_messages
from app.schemas.models import (
    Contact,
    ProfileSignals,
    SearchTrace,
    RawProduct,
    GiftRecommendation,
    HumanReview,
    HumanReviewStatus
)
from typing import TypedDict


class GraphState(TypedDict):
    contact: dict
    profile_signals: dict
    search_trace: dict
    raw_products: list
    validated_products: list
    recommended_gifts: list
    human_review: dict
    errors: list
    current_step: str
    search_retry_count: int
    reviewer_feedback: str