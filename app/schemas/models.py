from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


# ─────────────────────────────────────────
# INPUT SCHEMAS
# ─────────────────────────────────────────

class Experience(BaseModel):
    title: str
    company: str
    description: Optional[str] = ""


class LinkedInProfile(BaseModel):
    headline: str
    about: Optional[str] = ""
    experience: list[Experience] = []
    recent_posts: list[str] = []
    recent_comments: list[str] = []
    engaged_topics: list[str] = []


class RelationshipContext(BaseModel):
    relationship_type: str
    last_interaction: Optional[str] = ""
    business_goal: Optional[str] = ""


class GiftContext(BaseModel):
    occasion: str
    budget_min: float
    budget_max: float
    currency: str
    country: str


class Contact(BaseModel):
    name: str
    role: str
    company: str
    location: str
    linkedin_profile: LinkedInProfile
    relationship_context: RelationshipContext
    gift_context: GiftContext


# ─────────────────────────────────────────
# INTERMEDIATE SCHEMAS
# ─────────────────────────────────────────

class ProfileSignals(BaseModel):
    strong_signals: list[str] = []
    weak_signals: list[str] = []
    signals_to_avoid: list[str] = []


class SearchTrace(BaseModel):
    queries_used: list[str] = []
    products_considered_count: int = 0


class RawProduct(BaseModel):
    title: str
    url: str
    store: Optional[str] = ""
    price_raw: Optional[str] = ""
    price_numeric: Optional[float] = None
    is_url_valid: bool = False
    is_price_in_budget: bool = False
    snippet: Optional[str] = ""


# ─────────────────────────────────────────
# OUTPUT SCHEMAS
# ─────────────────────────────────────────

class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class GiftRecommendation(BaseModel):
    rank: int
    gift_name: str
    product_url: str
    store: str
    estimated_price: str
    why_this_gift: str
    personalisation_reasoning: str
    personalised_message: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    risk_level: RiskLevel
    assumptions: list[str] = []


class HumanReviewStatus(str, Enum):
    pending_review = "pending_review"
    approved = "approved"
    rejected = "rejected"
    edited = "edited"
    regenerate_requested = "regenerate_requested"


class HumanReview(BaseModel):
    status: HumanReviewStatus = HumanReviewStatus.pending_review
    available_actions: list[str] = ["approve", "reject", "edit", "regenerate"]
    reviewer_notes: Optional[str] = None


class ContactRecommendation(BaseModel):
    contact_name: str
    profile_signals: ProfileSignals
    search_trace: SearchTrace
    recommended_gifts: list[GiftRecommendation]
    human_review: HumanReview


# ─────────────────────────────────────────
# WORKFLOW STATE
# ─────────────────────────────────────────

class WorkflowState(BaseModel):
    contact: Optional[Contact] = None
    profile_signals: Optional[ProfileSignals] = None
    search_trace: SearchTrace = SearchTrace()
    raw_products: list[RawProduct] = []
    validated_products: list[RawProduct] = []
    recommended_gifts: list[GiftRecommendation] = []
    human_review: HumanReview = HumanReview()
    errors: list[str] = []
    current_step: str = "not_started"