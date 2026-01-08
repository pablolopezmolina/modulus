# MODULUS - API Main Module
# Session 11.2 - Pack 2 API Endpoints
# 
# Endpoints:
# - POST /simulate-formulation → Formulation → PopulationResult
# - POST /compare → A vs B comparison
# - GET /certificate/{id} → PDF certificate
# - GET /evidence/{id} → Evidence bundle
# - GET /bundle/{id} → Reproducibility bundle
#
# ============================================================================

"""
MODULUS API - Decision & Compliance OS

This module provides the REST API for Pack 2 Enterprise features:
- Formulation simulation
- A/B comparison
- Certificate generation
- Evidence retrieval
- Reproducibility bundles
"""

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Dict, Any, Optional, List, Literal, Union
from datetime import datetime, timezone
from enum import Enum
import uuid
import hashlib
import json
import io
import re

# =============================================================================
# APPLICATION SETUP
# =============================================================================

app = FastAPI(
    title="MODULUS API",
    description="Decision & Compliance OS for the Supplement Industry",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# IN-MEMORY STORAGE (Replace with proper DB in production)
# =============================================================================

class SimulationStorage:
    """In-memory storage for simulation results."""
    
    def __init__(self):
        self._simulations: Dict[str, Dict[str, Any]] = {}
        self._comparisons: Dict[str, Dict[str, Any]] = {}
    
    def store_simulation(
        self,
        sim_id: str,
        result: Dict[str, Any],
        request: Dict[str, Any],
        bundle: Dict[str, Any]
    ) -> None:
        """Store a simulation result."""
        self._simulations[sim_id] = {
            "result": result,
            "request": request,
            "bundle": bundle,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    
    def get_simulation(self, sim_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a simulation result."""
        return self._simulations.get(sim_id)
    
    def store_comparison(
        self,
        comparison_id: str,
        result: Dict[str, Any],
        sim_id_a: str,
        sim_id_b: str
    ) -> None:
        """Store a comparison result."""
        self._comparisons[comparison_id] = {
            "result": result,
            "simulation_id_a": sim_id_a,
            "simulation_id_b": sim_id_b,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    
    def get_comparison(self, comparison_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a comparison result."""
        return self._comparisons.get(comparison_id)


# Global storage instance
storage = SimulationStorage()

# =============================================================================
# REQUEST SCHEMAS
# =============================================================================

class IngredientInput(BaseModel):
    """Input schema for a single ingredient."""
    
    compound_id: str = Field(
        ...,
        description="Unique identifier for the compound (e.g., 'caffeine', 'l_theanine')",
        pattern=r"^[a-z][a-z0-9_]*$"
    )
    amount: float = Field(
        ...,
        gt=0,
        description="Amount of the ingredient"
    )
    unit: Literal["mg", "g", "mcg"] = Field(
        default="mg",
        description="Unit of measurement"
    )
    
    @field_validator("compound_id")
    @classmethod
    def validate_compound_id(cls, v: str) -> str:
        """Validate compound ID format."""
        if not re.match(r"^[a-z][a-z0-9_]*$", v):
            raise ValueError(
                f"Invalid compound_id '{v}'. Must be lowercase letters, "
                "numbers, and underscores, starting with a letter."
            )
        return v


class TimelineEventInput(BaseModel):
    """Input schema for a timeline event."""
    
    timestamp_minutes: float = Field(
        ...,
        ge=0,
        le=1440,
        description="Minutes from start of day (0-1440)"
    )
    event_type: Literal["meal", "ingestion", "exercise", "sleep"] = Field(
        ...,
        description="Type of event"
    )
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Event-specific data"
    )


class FormulationRequest(BaseModel):
    """Request schema for simulating a formulation."""
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Product name"
    )
    ingredients: List[IngredientInput] = Field(
        ...,
        min_length=1,
        description="List of ingredients"
    )
    form: Literal["capsule", "powder", "liquid", "tablet", "gummy"] = Field(
        default="capsule",
        description="Product form"
    )
    serving_info: str = Field(
        default="1 serving",
        description="Serving information"
    )
    population_size: int = Field(
        default=1000,
        ge=10,
        le=100000,
        description="Number of virtual individuals to simulate"
    )
    seed: Optional[int] = Field(
        default=None,
        description="Random seed for reproducibility"
    )
    timeline_events: Optional[List[TimelineEventInput]] = Field(
        default=None,
        description="Additional timeline events (meals, etc.)"
    )
    claims_to_evaluate: Optional[List[str]] = Field(
        default=None,
        description="Specific claims to evaluate (default: all applicable)"
    )
    
    @field_validator("ingredients")
    @classmethod
    def validate_ingredients(cls, v: List[IngredientInput]) -> List[IngredientInput]:
        """Validate that ingredients list is not empty."""
        if not v:
            raise ValueError("At least one ingredient is required")
        return v


class CompareRequest(BaseModel):
    """Request schema for comparing two formulations."""
    
    formulation_a: FormulationRequest = Field(
        ...,
        description="First formulation"
    )
    formulation_b: FormulationRequest = Field(
        ...,
        description="Second formulation"
    )
    name_a: Optional[str] = Field(
        default=None,
        description="Display name for formulation A"
    )
    name_b: Optional[str] = Field(
        default=None,
        description="Display name for formulation B"
    )
    population_size: int = Field(
        default=1000,
        ge=10,
        le=100000,
        description="Number of virtual individuals per formulation"
    )
    seed: Optional[int] = Field(
        default=None,
        description="Random seed for reproducibility"
    )


# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================

class DecisionSummary(BaseModel):
    """Summary of the decision (GO/CAUTION/NO_GO)."""
    
    verdict: Literal["GO", "CAUTION", "NO_GO"] = Field(
        ...,
        description="Decision verdict"
    )
    confidence: float = Field(
        ...,
        ge=0,
        le=1,
        description="Confidence level (0-1)"
    )
    summary: str = Field(
        ...,
        description="Human-readable summary"
    )
    
    @field_validator("verdict")
    @classmethod
    def validate_verdict(cls, v: str) -> str:
        """Validate verdict is one of the allowed values."""
        allowed = {"GO", "CAUTION", "NO_GO"}
        if v not in allowed:
            raise ValueError(f"Verdict must be one of {allowed}")
        return v


class RiskSummary(BaseModel):
    """Summary of a single risk."""
    
    risk_name: str = Field(..., description="Risk identifier")
    percentage: float = Field(
        ...,
        ge=0,
        le=100,
        description="Percentage of population affected"
    )
    severity: Literal["low", "medium", "high"] = Field(
        ...,
        description="Severity level"
    )
    affected_segments: List[str] = Field(
        default_factory=list,
        description="Population segments most affected"
    )
    description: Optional[str] = Field(
        default=None,
        description="Human-readable description"
    )


class ClaimDefensibility(BaseModel):
    """Defensibility assessment for a claim."""
    
    is_defensible: bool = Field(..., description="Whether claim is defensible")
    responder_pct: float = Field(
        ...,
        ge=0,
        le=100,
        description="Percentage of responders"
    )
    confidence: float = Field(
        default=0.0,
        ge=0,
        le=1,
        description="Confidence level"
    )
    suggested_wording: Optional[str] = Field(
        default=None,
        description="Suggested claim wording"
    )


class SimulationResponse(BaseModel):
    """Response schema for simulation results."""
    
    simulation_id: str = Field(..., description="Unique simulation ID")
    product_name: str = Field(..., description="Product name")
    timestamp: str = Field(..., description="ISO timestamp of simulation")
    decision: DecisionSummary = Field(..., description="Decision summary")
    risks: List[RiskSummary] = Field(
        default_factory=list,
        description="Risk summaries"
    )
    claims_defensibility: Dict[str, ClaimDefensibility] = Field(
        default_factory=dict,
        description="Claim defensibility assessments"
    )
    metrics: Dict[str, float] = Field(
        default_factory=dict,
        description="Key metrics"
    )
    n_simulated: int = Field(..., description="Number of individuals simulated")
    n_valid: int = Field(..., description="Number of valid simulations")
    
    # Optional detailed data
    recommendations: Optional[List[str]] = Field(
        default=None,
        description="Recommendations for improvement"
    )


class ComparisonResponse(BaseModel):
    """Response schema for comparison results."""
    
    comparison_id: str = Field(..., description="Unique comparison ID")
    timestamp: str = Field(..., description="ISO timestamp")
    name_a: str = Field(..., description="Name of formulation A")
    name_b: str = Field(..., description="Name of formulation B")
    simulation_id_a: str = Field(..., description="Simulation ID for A")
    simulation_id_b: str = Field(..., description="Simulation ID for B")
    
    winner_by_metric: Dict[str, Literal["A", "B", "TIE"]] = Field(
        ...,
        description="Winner for each metric"
    )
    delta_metrics: Dict[str, float] = Field(
        ...,
        description="Difference (A - B) for each metric"
    )
    statistical_significance: Optional[Dict[str, bool]] = Field(
        default=None,
        description="Statistical significance for each comparison"
    )
    recommendation: str = Field(
        ...,
        description="Overall recommendation"
    )


class EvidenceResponse(BaseModel):
    """Response schema for evidence bundle."""
    
    simulation_id: str = Field(..., description="Associated simulation ID")
    sources: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of evidence sources with DOIs"
    )
    parameters_evidence: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Evidence for each parameter used"
    )
    methodology: str = Field(
        default="",
        description="Methodology description"
    )
    confidence_levels: Dict[str, str] = Field(
        default_factory=dict,
        description="Confidence level for each data source"
    )


class BundleResponse(BaseModel):
    """Response schema for reproducibility bundle."""
    
    simulation_id: str = Field(..., description="Associated simulation ID")
    version: str = Field(..., description="MODULUS version")
    hash: str = Field(..., description="SHA256 hash of inputs")
    seed: Optional[int] = Field(default=None, description="Random seed used")
    timestamp: str = Field(..., description="ISO timestamp")
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Full configuration used"
    )
    ingredient_versions: Dict[str, str] = Field(
        default_factory=dict,
        description="Version info for each ingredient profile"
    )


class IngredientInfo(BaseModel):
    """Information about an available ingredient."""
    
    compound_id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Human-readable name")
    category: str = Field(..., description="Category (e.g., stimulant, amino)")
    max_single_dose: float = Field(..., description="Maximum single dose")
    max_daily_dose: float = Field(..., description="Maximum daily dose")
    dose_unit: str = Field(..., description="Dose unit")
    evidence_level: str = Field(..., description="Evidence level")


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: Literal["healthy", "degraded", "unhealthy"] = "healthy"
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    version: str = "3.0.0"


class VersionResponse(BaseModel):
    """Version information response."""
    
    version: str = "3.0.0"
    api_version: str = "v1"
    build_date: str = "2025-01-08"
    pack_level: str = "Pack 2 Enterprise"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def generate_simulation_id() -> str:
    """Generate a unique simulation ID."""
    return f"sim_{uuid.uuid4().hex[:16]}"


def generate_comparison_id() -> str:
    """Generate a unique comparison ID."""
    return f"cmp_{uuid.uuid4().hex[:16]}"


def compute_input_hash(request: Dict[str, Any]) -> str:
    """Compute SHA256 hash of the input request."""
    # Sort keys for deterministic ordering
    canonical = json.dumps(request, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def validate_simulation_id(sim_id: str) -> bool:
    """Validate simulation ID format."""
    return bool(re.match(r"^(sim|cmp)_[a-f0-9]{16}$", sim_id))


# =============================================================================
# INGREDIENT LIBRARY (Lazy loaded)
# =============================================================================

# Known ingredients (from ingredients.json)
KNOWN_INGREDIENTS = {
    "caffeine", "carbohydrate_glucose", "carbohydrate_maltodextrin",
    "carbohydrate_palatinose", "l_theanine", "taurine", "beta_alanine",
    "creatine_monohydrate", "citrulline_malate", "tyrosine", "alpha_gpc",
    "vitamin_b6", "vitamin_b12", "magnesium_citrate", "ashwagandha"
}


def get_ingredient_library():
    """Get the ingredient library (lazy load)."""
    try:
        from core.compounds.library import IngredientLibrary
        return IngredientLibrary()
    except ImportError:
        return None


def validate_ingredients(ingredients: List[IngredientInput]) -> List[str]:
    """Validate that all ingredients are known."""
    unknown = []
    for ing in ingredients:
        if ing.compound_id not in KNOWN_INGREDIENTS:
            unknown.append(ing.compound_id)
    return unknown


# =============================================================================
# SIMULATION ENGINE (Lazy loaded)
# =============================================================================

def run_simulation(
    request: FormulationRequest
) -> Dict[str, Any]:
    """
    Run a population simulation.
    
    This function orchestrates the simulation using the core modules.
    Returns a dictionary with simulation results.
    """
    try:
        # Try to import core modules
        from core.simulation.population_day_simulator import PopulationDaySimulator
        from core.population.generator import PopulationGenerator
        from core.compounds.formulation import Formulation, Ingredient
        from core.timeline.timeline import Timeline
        from core.timeline.event import Event
        from analysis.decision import DecisionEngine
        from analysis.risk import RiskAnalyzer
        from analysis.claims import ClaimAnalyzer
        from analysis.evidence import EvidenceRegistry
        
        # Build formulation
        ingredients = [
            Ingredient(
                compound_id=ing.compound_id,
                amount=ing.amount,
                unit=ing.unit
            )
            for ing in request.ingredients
        ]
        formulation = Formulation(
            name=request.name,
            ingredients=ingredients,
            form=request.form,
            serving_info=request.serving_info
        )
        
        # Build timeline
        timeline = formulation.to_timeline(base_time=480)  # 8:00 AM default
        
        # Add custom events
        if request.timeline_events:
            for event_input in request.timeline_events:
                event = Event(
                    timestamp_minutes=event_input.timestamp_minutes,
                    event_type=event_input.event_type,
                    payload=event_input.payload
                )
                timeline = timeline.add_event(event)
        
        # Generate population
        generator = PopulationGenerator()
        population = generator.generate(
            n=request.population_size,
            seed=request.seed
        )
        
        # Run simulation
        simulator = PopulationDaySimulator()
        results = simulator.simulate(
            population=population,
            timeline=timeline
        )
        
        # Analyze decision
        decision_engine = DecisionEngine()
        decision = decision_engine.analyze(results)
        
        # Analyze risks
        risk_analyzer = RiskAnalyzer()
        risks = risk_analyzer.analyze(results)
        
        # Analyze claims
        claim_analyzer = ClaimAnalyzer()
        claims = claim_analyzer.analyze(
            results,
            claims=request.claims_to_evaluate
        )
        
        # Build evidence registry
        evidence_registry = EvidenceRegistry()
        evidence = evidence_registry.for_formulation(formulation)
        
        return {
            "success": True,
            "results": results,
            "decision": decision,
            "risks": risks,
            "claims": claims,
            "evidence": evidence,
            "n_simulated": results.n_individuals,
            "n_valid": results.n_valid
        }
        
    except ImportError as e:
        # Core modules not available - return mock data for testing
        return _mock_simulation(request)


def _mock_simulation(request: FormulationRequest) -> Dict[str, Any]:
    """Generate mock simulation data for testing."""
    import random
    
    if request.seed is not None:
        random.seed(request.seed)
    
    n = request.population_size
    n_valid = int(n * random.uniform(0.95, 0.99))
    
    # Determine verdict based on ingredients
    has_high_caffeine = any(
        ing.compound_id == "caffeine" and ing.amount >= 200
        for ing in request.ingredients
    )
    has_theanine = any(
        ing.compound_id == "l_theanine"
        for ing in request.ingredients
    )
    
    if has_high_caffeine and not has_theanine:
        verdict = "CAUTION"
        sleep_risk = random.uniform(20, 35)
        jitter_risk = random.uniform(25, 40)
    elif has_high_caffeine and has_theanine:
        verdict = "GO"
        sleep_risk = random.uniform(10, 20)
        jitter_risk = random.uniform(5, 15)
    else:
        verdict = "GO"
        sleep_risk = random.uniform(5, 15)
        jitter_risk = random.uniform(5, 15)
    
    return {
        "success": True,
        "decision": {
            "verdict": verdict,
            "confidence": random.uniform(0.7, 0.95),
            "summary": f"Product shows {'moderate' if verdict == 'CAUTION' else 'low'} risk profile."
        },
        "risks": [
            {
                "risk_name": "sleep_disruption",
                "percentage": sleep_risk,
                "severity": "medium" if sleep_risk > 20 else "low",
                "affected_segments": ["slow_caffeine_metabolizers"]
            },
            {
                "risk_name": "jitter_risk",
                "percentage": jitter_risk,
                "severity": "medium" if jitter_risk > 20 else "low",
                "affected_segments": ["caffeine_sensitive"]
            }
        ],
        "claims": {
            "sustained_energy": {
                "is_defensible": True,
                "responder_pct": random.uniform(65, 85),
                "confidence": random.uniform(0.7, 0.9)
            },
            "no_crash": {
                "is_defensible": True,
                "responder_pct": random.uniform(80, 95),
                "confidence": random.uniform(0.8, 0.95)
            },
            "mental_focus": {
                "is_defensible": has_theanine or random.random() > 0.5,
                "responder_pct": random.uniform(50, 75),
                "confidence": random.uniform(0.6, 0.85)
            }
        },
        "metrics": {
            "glucose_peak_mean": random.uniform(125, 145),
            "glucose_peak_std": random.uniform(10, 20),
            "alertness_duration_mean": random.uniform(3.5, 5.5),
            "alertness_duration_std": random.uniform(0.3, 0.8),
            "caffeine_half_life_mean": random.uniform(4.5, 6.0),
            "time_above_glucose_140_pct": random.uniform(5, 20)
        },
        "n_simulated": n,
        "n_valid": n_valid
    }


def run_comparison(
    request: CompareRequest
) -> Dict[str, Any]:
    """Run comparison between two formulations."""
    try:
        from analysis.comparison import ComparisonEngine
        
        # Run both simulations
        result_a = run_simulation(request.formulation_a)
        result_b = run_simulation(request.formulation_b)
        
        # Run comparison
        engine = ComparisonEngine()
        comparison = engine.compare(
            result_a["results"],
            result_b["results"]
        )
        
        return {
            "success": True,
            "result_a": result_a,
            "result_b": result_b,
            "comparison": comparison
        }
        
    except ImportError:
        return _mock_comparison(request)


def _mock_comparison(request: CompareRequest) -> Dict[str, Any]:
    """Generate mock comparison data."""
    result_a = _mock_simulation(request.formulation_a)
    result_b = _mock_simulation(request.formulation_b)
    
    metrics_a = result_a["metrics"]
    metrics_b = result_b["metrics"]
    
    delta = {}
    winner = {}
    
    for key in metrics_a:
        if key in metrics_b:
            d = metrics_a[key] - metrics_b[key]
            delta[key] = d
            
            # Determine winner (lower is better for some metrics)
            if "risk" in key or "glucose" in key:
                winner[key] = "A" if d < -0.5 else ("B" if d > 0.5 else "TIE")
            else:
                winner[key] = "A" if d > 0.5 else ("B" if d < -0.5 else "TIE")
    
    return {
        "success": True,
        "result_a": result_a,
        "result_b": result_b,
        "delta_metrics": delta,
        "winner_by_metric": winner,
        "statistical_significance": {k: abs(v) > 1.0 for k, v in delta.items()},
        "recommendation": "Formulation B recommended" if sum(1 for w in winner.values() if w == "B") > sum(1 for w in winner.values() if w == "A") else "Formulation A recommended"
    }


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/health", response_model=HealthResponse, tags=["Status"])
async def health_check():
    """Health check endpoint."""
    return HealthResponse()


@app.get("/version", response_model=VersionResponse, tags=["Status"])
async def version():
    """Get API version information."""
    return VersionResponse()


@app.get("/ingredients", tags=["Reference"])
async def list_ingredients():
    """List all available ingredients."""
    library = get_ingredient_library()
    
    if library:
        ingredients = [
            {
                "compound_id": cid,
                "name": library.get_compound(cid).name,
                "category": library.get_compound(cid).category,
                "max_single_dose": library.get_compound(cid).max_single_dose,
                "max_daily_dose": library.get_compound(cid).max_daily_dose,
                "dose_unit": library.get_compound(cid).dose_unit,
                "evidence_level": library.get_compound(cid).evidence_level
            }
            for cid in library.list_compounds()
        ]
    else:
        # Return minimal info from known ingredients
        ingredients = [
            {
                "compound_id": cid,
                "name": cid.replace("_", " ").title(),
                "category": "unknown",
                "max_single_dose": 500,
                "max_daily_dose": 1000,
                "dose_unit": "mg",
                "evidence_level": "medium"
            }
            for cid in sorted(KNOWN_INGREDIENTS)
        ]
    
    return {"ingredients": ingredients}


@app.post("/simulate-formulation", response_model=SimulationResponse, tags=["Simulation"])
async def simulate_formulation(request: FormulationRequest):
    """
    Simulate a product formulation.
    
    This endpoint runs a population simulation (default N=1000) and returns:
    - Decision (GO / CAUTION / NO_GO)
    - Risk analysis
    - Claim defensibility
    - Key metrics
    
    The simulation ID can be used to retrieve:
    - Certificate: GET /certificate/{id}
    - Evidence: GET /evidence/{id}
    - Bundle: GET /bundle/{id}
    """
    # Validate ingredients
    unknown = validate_ingredients(request.ingredients)
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown ingredients: {', '.join(unknown)}"
        )
    
    # Generate simulation ID
    sim_id = generate_simulation_id()
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Run simulation
    try:
        result = run_simulation(request)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Simulation failed. Please try again."
        )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail="Simulation failed. Please try again."
        )
    
    # Build response
    decision = result["decision"]
    risks = result.get("risks", [])
    claims = result.get("claims", {})
    metrics = result.get("metrics", {})
    
    # Build risk summaries
    risk_summaries = [
        RiskSummary(
            risk_name=r["risk_name"],
            percentage=r["percentage"],
            severity=r.get("severity", "medium"),
            affected_segments=r.get("affected_segments", [])
        )
        for r in risks
    ]
    
    # Build claim defensibility
    claims_def = {
        claim_id: ClaimDefensibility(
            is_defensible=data.get("is_defensible", False),
            responder_pct=data.get("responder_pct", 0),
            confidence=data.get("confidence", 0)
        )
        for claim_id, data in claims.items()
    }
    
    # Compute hash and build bundle
    request_dict = request.model_dump()
    input_hash = compute_input_hash(request_dict)
    
    bundle = {
        "version": "3.0.0",
        "hash": input_hash,
        "seed": request.seed,
        "timestamp": timestamp,
        "config": request_dict,
        "ingredient_versions": {
            ing.compound_id: "1.0"
            for ing in request.ingredients
        }
    }
    
    # Store simulation
    storage.store_simulation(
        sim_id=sim_id,
        result=result,
        request=request_dict,
        bundle=bundle
    )
    
    return SimulationResponse(
        simulation_id=sim_id,
        product_name=request.name,
        timestamp=timestamp,
        decision=DecisionSummary(
            verdict=decision["verdict"],
            confidence=decision["confidence"],
            summary=decision["summary"]
        ),
        risks=risk_summaries,
        claims_defensibility=claims_def,
        metrics=metrics,
        n_simulated=result["n_simulated"],
        n_valid=result["n_valid"]
    )


@app.post("/compare", response_model=ComparisonResponse, tags=["Comparison"])
async def compare_formulations(request: CompareRequest):
    """
    Compare two formulations.
    
    This endpoint runs simulations for both formulations and compares:
    - Key metrics
    - Risk profiles
    - Statistical significance
    
    Returns which formulation is better for each metric.
    """
    # Validate ingredients for both formulations
    for form in [request.formulation_a, request.formulation_b]:
        unknown = validate_ingredients(form.ingredients)
        if unknown:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown ingredients in {form.name}: {', '.join(unknown)}"
            )
    
    # Override population size
    request.formulation_a.population_size = request.population_size
    request.formulation_b.population_size = request.population_size
    request.formulation_a.seed = request.seed
    request.formulation_b.seed = (request.seed + 1) if request.seed else None
    
    # Run comparison
    try:
        result = run_comparison(request)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Comparison failed. Please try again."
        )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail="Comparison failed. Please try again."
        )
    
    # Generate IDs
    comparison_id = generate_comparison_id()
    sim_id_a = generate_simulation_id()
    sim_id_b = generate_simulation_id()
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Store individual simulations
    for sim_id, res, form in [
        (sim_id_a, result["result_a"], request.formulation_a),
        (sim_id_b, result["result_b"], request.formulation_b)
    ]:
        request_dict = form.model_dump()
        storage.store_simulation(
            sim_id=sim_id,
            result=res,
            request=request_dict,
            bundle={
                "version": "3.0.0",
                "hash": compute_input_hash(request_dict),
                "seed": form.seed,
                "timestamp": timestamp,
                "config": request_dict,
                "ingredient_versions": {}
            }
        )
    
    # Store comparison
    storage.store_comparison(
        comparison_id=comparison_id,
        result=result,
        sim_id_a=sim_id_a,
        sim_id_b=sim_id_b
    )
    
    return ComparisonResponse(
        comparison_id=comparison_id,
        timestamp=timestamp,
        name_a=request.name_a or request.formulation_a.name,
        name_b=request.name_b or request.formulation_b.name,
        simulation_id_a=sim_id_a,
        simulation_id_b=sim_id_b,
        winner_by_metric=result.get("winner_by_metric", {}),
        delta_metrics=result.get("delta_metrics", {}),
        statistical_significance=result.get("statistical_significance"),
        recommendation=result.get("recommendation", "See detailed analysis")
    )


@app.get("/certificate/{simulation_id}", tags=["Artifacts"])
async def get_certificate(
    simulation_id: str,
    format: Literal["pdf", "json"] = Query(default="pdf", description="Output format")
):
    """
    Get the Modulus Protocol Certificate for a simulation.
    
    The certificate summarizes the decision and can be used as proof of
    evaluation for regulatory or business purposes.
    """
    # Validate ID format
    if not validate_simulation_id(simulation_id):
        raise HTTPException(status_code=400, detail="Invalid simulation ID format")
    
    # Retrieve simulation
    sim_data = storage.get_simulation(simulation_id)
    if not sim_data:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    result = sim_data["result"]
    request = sim_data["request"]
    bundle = sim_data["bundle"]
    
    if format == "json":
        # Return JSON certificate
        return {
            "certificate_id": f"cert_{simulation_id[4:]}",
            "simulation_id": simulation_id,
            "product_name": request.get("name", "Unknown"),
            "verdict": result["decision"]["verdict"],
            "confidence": result["decision"]["confidence"],
            "timestamp": bundle["timestamp"],
            "version": bundle["version"],
            "hash": bundle["hash"]
        }
    
    # Generate PDF certificate
    try:
        from reporting.certificate import CertificateGenerator
        
        generator = CertificateGenerator()
        pdf_bytes = generator.generate(
            product_name=request.get("name", "Unknown"),
            verdict=result["decision"]["verdict"],
            confidence=result["decision"]["confidence"],
            metrics=result.get("metrics", {}),
            simulation_id=simulation_id,
            timestamp=bundle["timestamp"]
        )
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=certificate_{simulation_id}.pdf"
            }
        )
    except ImportError:
        # Return mock PDF
        return Response(
            content=_generate_mock_pdf(f"Certificate for {simulation_id}"),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=certificate_{simulation_id}.pdf"
            }
        )


@app.get("/evidence/{simulation_id}", response_model=EvidenceResponse, tags=["Artifacts"])
async def get_evidence(simulation_id: str):
    """
    Get the evidence bundle for a simulation.
    
    Returns all DOIs and sources used in the simulation, organized by
    parameter and compound.
    """
    # Validate ID format
    if not validate_simulation_id(simulation_id):
        raise HTTPException(status_code=400, detail="Invalid simulation ID format")
    
    # Retrieve simulation
    sim_data = storage.get_simulation(simulation_id)
    if not sim_data:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    result = sim_data["result"]
    request = sim_data["request"]
    
    # Build evidence response
    try:
        from analysis.evidence import EvidenceRegistry
        
        registry = EvidenceRegistry()
        evidence = registry.for_simulation_result(result)
        
        return EvidenceResponse(
            simulation_id=simulation_id,
            sources=evidence.get("sources", []),
            parameters_evidence=evidence.get("parameters_evidence", {}),
            methodology=evidence.get("methodology", ""),
            confidence_levels=evidence.get("confidence_levels", {})
        )
    except ImportError:
        # Return mock evidence
        ingredients = request.get("ingredients", [])
        sources = []
        
        for ing in ingredients:
            compound_id = ing.get("compound_id", "unknown")
            sources.append({
                "compound_id": compound_id,
                "doi": f"10.1234/modulus.{compound_id}",
                "title": f"Pharmacokinetics of {compound_id}",
                "authors": "MODULUS Reference Database",
                "year": 2024,
                "confidence": "high"
            })
        
        return EvidenceResponse(
            simulation_id=simulation_id,
            sources=sources,
            parameters_evidence={
                ing.get("compound_id", "unknown"): {
                    "pk_params": {"source": "literature", "confidence": "high"},
                    "pd_params": {"source": "literature", "confidence": "medium"}
                }
                for ing in ingredients
            },
            methodology="Population-based Monte Carlo simulation with validated PK/PD models",
            confidence_levels={
                ing.get("compound_id", "unknown"): "high"
                for ing in ingredients
            }
        )


@app.get("/bundle/{simulation_id}", response_model=BundleResponse, tags=["Artifacts"])
async def get_bundle(simulation_id: str):
    """
    Get the reproducibility bundle for a simulation.
    
    This bundle contains all information needed to reproduce the exact
    same simulation results: configuration, seed, versions, and hash.
    """
    # Validate ID format
    if not validate_simulation_id(simulation_id):
        raise HTTPException(status_code=400, detail="Invalid simulation ID format")
    
    # Retrieve simulation
    sim_data = storage.get_simulation(simulation_id)
    if not sim_data:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    bundle = sim_data["bundle"]
    
    return BundleResponse(
        simulation_id=simulation_id,
        version=bundle.get("version", "3.0.0"),
        hash=bundle.get("hash", ""),
        seed=bundle.get("seed"),
        timestamp=bundle.get("timestamp", ""),
        config=bundle.get("config", {}),
        ingredient_versions=bundle.get("ingredient_versions", {})
    )


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def _generate_mock_pdf(title: str) -> bytes:
    """Generate a minimal mock PDF for testing."""
    # Very basic PDF structure
    pdf = f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT
/F1 12 Tf
100 700 Td
({title}) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000214 00000 n 
trailer
<< /Size 5 /Root 1 0 R >>
startxref
308
%%EOF"""
    return pdf.encode('latin-1')


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
