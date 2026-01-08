"""
MODULUS - Consumer Web App v1.2
Session 15-17: FastAPI app with templates, personalization, and analytics

Features:
- White-label consumer web app for brands
- Personalization engine
- Real-time API (<100ms)
- Analytics dashboard for brand clients

Version History:
- v1.0: Basic consumer web app
- v1.1: Fixed routes, added 60 tests
- v1.2: Added analytics tracking and dashboard
"""
from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
import os

# Import analytics
from webapp.analytics import get_analytics_service

# Import personalization (and re-export for test compatibility)
from webapp.personalization import (
    PersonalizationEngine, 
    UserInput, 
    PersonalizationResult,
    CaffeineSensitivity
)

# Import brand config (and re-export for test compatibility)
from webapp.config import BrandConfig, get_brand_config, PRESET_BRANDS


# =============================================================================
# Product Config (defined here - re-exported for test compatibility)
# =============================================================================

@dataclass
class ProductConfig:
    """Configuration for a product."""
    product_id: str
    name: str
    caffeine_mg: float = 0
    has_theanine: bool = False
    category: str = "general"
    
    def model_dump(self) -> Dict[str, Any]:
        """Convert to dictionary for template rendering."""
        return {
            "product_id": self.product_id,
            "name": self.name,
            "caffeine_mg": self.caffeine_mg,
            "has_theanine": self.has_theanine,
            "category": self.category
        }


# =============================================================================
# App Configuration
# =============================================================================

app = FastAPI(
    title="MODULUS Consumer App",
    description="Personalized supplement timing powered by MODULUS",
    version="1.2.0"
)

# Static files and templates
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Personalization engine (exported for tests)
engine = PersonalizationEngine()


# =============================================================================
# Demo Data
# =============================================================================

DEMO_PRODUCTS = {
    "energy_pro": ProductConfig(
        product_id="energy_pro",
        name="Energy Pro",
        caffeine_mg=150,
        has_theanine=True,
        category="pre_workout"
    ),
    "focus_max": ProductConfig(
        product_id="focus_max",
        name="Focus Max",
        caffeine_mg=100,
        has_theanine=True,
        category="cognitive"
    ),
    "endurance_plus": ProductConfig(
        product_id="endurance_plus",
        name="Endurance Plus",
        caffeine_mg=200,
        has_theanine=False,
        category="endurance"
    ),
    "sleep_well": ProductConfig(
        product_id="sleep_well",
        name="Sleep Well",
        caffeine_mg=0,
        has_theanine=True,
        category="sleep"
    ),
    "morning_boost": ProductConfig(
        product_id="morning_boost",
        name="Morning Boost",
        caffeine_mg=80,
        has_theanine=False,
        category="energy"
    )
}

# Map brands to their products
BRAND_PRODUCTS = {
    "energyx": ["energy_pro", "endurance_plus", "morning_boost"],
    "modulus": ["energy_pro", "focus_max", "sleep_well"],
    "vitaboost": ["sleep_well", "morning_boost"],
    "peakform": ["endurance_plus", "energy_pro"]
}


# =============================================================================
# Pydantic Models
# =============================================================================

class PersonalizationRequest(BaseModel):
    """API request for personalization."""
    product_id: str
    weight_kg: float = Field(ge=30, le=200)
    caffeine_sensitivity: str = Field(pattern="^(slow|normal|fast)$")
    activity_time: str = Field(pattern="^[0-2][0-9]:[0-5][0-9]$")
    wake_time: Optional[str] = Field(default="07:00", pattern="^[0-2][0-9]:[0-5][0-9]$")
    sleep_time: Optional[str] = Field(default="23:00", pattern="^[0-2][0-9]:[0-5][0-9]$")


class PersonalizationResponse(BaseModel):
    """API response for personalization."""
    product_id: str
    optimal_timing: str
    dosage_multiplier: float
    expected_effect: Dict[str, Any]
    warnings: List[str]
    response_time_ms: float


class TrackEventRequest(BaseModel):
    """API request for tracking events."""
    event_type: str
    brand_id: str
    product_id: str
    data: Dict[str, Any] = {}


# =============================================================================
# Health Check
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# =============================================================================
# API Routes (BEFORE wildcard routes)
# =============================================================================

@app.get("/api/products")
async def list_products():
    """List all available products."""
    return {
        "products": [
            {"id": k, "name": v.name, "category": v.category}
            for k, v in DEMO_PRODUCTS.items()
        ]
    }


@app.get("/api/brands")
async def list_brands():
    """List all available brands."""
    return {
        "brands": [
            {
                "id": brand_id, 
                "name": get_brand_config(brand_id).brand_name, 
                "products": BRAND_PRODUCTS.get(brand_id, [])
            }
            for brand_id in PRESET_BRANDS.keys()
        ]
    }


@app.post("/api/personalize")
async def api_personalize(request: PersonalizationRequest):
    """
    Personalize product timing via API.
    Target: <100ms response time
    """
    import time
    start = time.time()
    
    product = DEMO_PRODUCTS.get(request.product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product '{request.product_id}' not found")
    
    user_input = UserInput(
        weight_kg=request.weight_kg,
        caffeine_sensitivity=request.caffeine_sensitivity,
        activity_time=request.activity_time,
        wake_time=request.wake_time or "07:00",
        sleep_time=request.sleep_time or "23:00"
    )
    
    result = engine.personalize(user_input, product)
    elapsed = (time.time() - start) * 1000
    
    # Track analytics
    service = get_analytics_service()
    service.track_personalization(
        brand_id="api",
        product_id=request.product_id,
        user_data={
            "weight_kg": request.weight_kg,
            "caffeine_sensitivity": request.caffeine_sensitivity,
            "activity_time": request.activity_time
        },
        result={
            "optimal_timing": result.optimal_timing,
            "response_time_ms": elapsed
        }
    )
    
    return PersonalizationResponse(
        product_id=request.product_id,
        optimal_timing=result.optimal_timing,
        dosage_multiplier=result.dosage_multiplier,
        expected_effect=result.expected_effect,
        warnings=result.warnings,
        response_time_ms=round(elapsed, 2)
    )


# =============================================================================
# Analytics API Routes
# =============================================================================

@app.get("/api/analytics/dashboard")
async def get_analytics_dashboard(brand_id: Optional[str] = None):
    """Get analytics dashboard summary."""
    service = get_analytics_service()
    summary = service.get_dashboard_summary(brand_id=brand_id)
    return summary


@app.post("/api/analytics/track")
async def track_analytics_event(request: TrackEventRequest):
    """Track an analytics event."""
    service = get_analytics_service()
    
    if request.event_type == "page_view":
        service.track_page_view(
            request.brand_id, 
            request.product_id, 
            request.data.get("page", "unknown")
        )
    elif request.event_type == "form_start":
        service.track_form_start(request.brand_id, request.product_id)
    elif request.event_type == "personalization":
        service.track_personalization(
            request.brand_id, 
            request.product_id,
            request.data.get("user_data", {}),
            request.data.get("result", {})
        )
    
    return {"status": "ok", "event_type": request.event_type}


@app.get("/api/analytics/export")
async def export_analytics(
    brand_id: Optional[str] = None,
    include_events: bool = False
):
    """Export analytics data as JSON."""
    service = get_analytics_service()
    json_data = service.export_to_json(
        brand_id=brand_id,
        include_events=include_events
    )
    return Response(
        content=json_data,
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=modulus-analytics-{brand_id or 'all'}.json"
        }
    )


# =============================================================================
# Web Routes
# =============================================================================

@app.get("/")
async def root():
    """Redirect root to demo brand."""
    return RedirectResponse(url="/energyx/energy_pro")


@app.get("/{brand_id}/dashboard")
async def dashboard_page(request: Request, brand_id: str):
    """Analytics dashboard page for brand owners."""
    brand_config = get_brand_config(brand_id)
    if brand_id not in PRESET_BRANDS:
        raise HTTPException(status_code=404, detail=f"Brand '{brand_id}' not found")
    
    service = get_analytics_service()
    summary = service.get_dashboard_summary(brand_id=brand_id)
    
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "brand": {
                "id": brand_id,
                "name": brand_config.brand_name,
                "primary_color": brand_config.primary_color,
                "secondary_color": brand_config.secondary_color
            },
            "summary": summary
        }
    )


@app.get("/{brand_id}/{product_id}")
async def landing_page(request: Request, brand_id: str, product_id: str):
    """Product landing page."""
    brand_config = get_brand_config(brand_id)
    if brand_id not in PRESET_BRANDS:
        raise HTTPException(status_code=404, detail=f"Brand '{brand_id}' not found")
    
    product = DEMO_PRODUCTS.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found")
    
    # Track page view
    service = get_analytics_service()
    service.track_page_view(brand_id, product_id, "landing")
    
    return templates.TemplateResponse(
        request=request,
        name="landing.html",
        context={
            "brand": brand_config.to_dict(),
            "product": product.model_dump()
        }
    )


@app.get("/{brand_id}/{product_id}/form")
async def form_page(request: Request, brand_id: str, product_id: str):
    """Personalization form page."""
    brand_config = get_brand_config(brand_id)
    if brand_id not in PRESET_BRANDS:
        raise HTTPException(status_code=404, detail=f"Brand '{brand_id}' not found")
    
    product = DEMO_PRODUCTS.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found")
    
    # Track page view and form start
    service = get_analytics_service()
    service.track_page_view(brand_id, product_id, "form")
    service.track_form_start(brand_id, product_id)
    
    return templates.TemplateResponse(
        request=request,
        name="form.html",
        context={
            "brand": brand_config.to_dict(),
            "product": product.model_dump()
        }
    )


@app.post("/{brand_id}/{product_id}/result")
async def result_page(
    request: Request,
    brand_id: str,
    product_id: str,
    weight_kg: float = Form(...),
    caffeine_sensitivity: str = Form(...),
    activity_time: str = Form(...),
    wake_time: str = Form(default="07:00"),
    sleep_time: str = Form(default="23:00")
):
    """Personalization result page."""
    import time
    start = time.time()
    
    brand_config = get_brand_config(brand_id)
    if brand_id not in PRESET_BRANDS:
        raise HTTPException(status_code=404, detail=f"Brand '{brand_id}' not found")
    
    product = DEMO_PRODUCTS.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found")
    
    user_input = UserInput(
        weight_kg=weight_kg,
        caffeine_sensitivity=caffeine_sensitivity,
        activity_time=activity_time,
        wake_time=wake_time,
        sleep_time=sleep_time
    )
    
    result = engine.personalize(user_input, product)
    elapsed = (time.time() - start) * 1000
    
    # Track personalization
    service = get_analytics_service()
    service.track_personalization(
        brand_id=brand_id,
        product_id=product_id,
        user_data={
            "weight_kg": weight_kg,
            "caffeine_sensitivity": caffeine_sensitivity,
            "activity_time": activity_time,
            "wake_time": wake_time,
            "sleep_time": sleep_time
        },
        result={
            "optimal_timing": result.optimal_timing,
            "dosage_multiplier": result.dosage_multiplier,
            "response_time_ms": elapsed
        }
    )
    
    return templates.TemplateResponse(
        request=request,
        name="result.html",
        context={
            "brand": brand_config.to_dict(),
            "product": product.model_dump(),
            "user_input": user_input.model_dump(),
            "result": result.model_dump(),
            "response_time_ms": round(elapsed, 2)
        }
    )
