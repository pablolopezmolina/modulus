"""
MODULUS Consumer Web App - FastAPI Application

Main web application with API endpoints and template rendering.

Session 15.1 - FASE 5: Pack 3

Endpoints:
- GET /{brand_id}/{product_id} - Landing page
- GET /{brand_id}/{product_id}/form - User input form
- POST /{brand_id}/{product_id}/personalize - Get personalization
- GET /{brand_id}/{product_id}/result - Results page

API Endpoints:
- POST /api/personalize - JSON API for personalization
- GET /api/products - List available products
- GET /api/brands - List available brands
"""
import os
from typing import Dict, Any, Optional
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from .personalization import (
    PersonalizationEngine,
    ProductConfig,
    UserInput,
    PersonalizationResult
)
from .config import (
    BrandConfig,
    AppConfig,
    PRESET_BRANDS,
    get_brand_config
)


# =============================================================================
# APP SETUP
# =============================================================================

app = FastAPI(
    title="MODULUS Consumer App",
    description="Personalized supplement timing recommendations",
    version="1.0.0"
)

# Template directory (relative to this file)
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# Initialize templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Mount static files
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Initialize personalization engine
engine = PersonalizationEngine()

# Register some demo products
DEMO_PRODUCTS = [
    ProductConfig(
        product_id="energy_pro",
        name="Energy Pro",
        caffeine_mg=200,
        has_theanine=True,
        other_stimulants_mg=25,
        serving_instructions="Mix 1 scoop with 8-12 oz water",
        description="Premium pre-workout with balanced energy"
    ),
    ProductConfig(
        product_id="pure_focus",
        name="Pure Focus",
        caffeine_mg=150,
        has_theanine=True,
        other_stimulants_mg=0,
        serving_instructions="Take 2 capsules with water",
        description="Clean energy for mental clarity"
    ),
    ProductConfig(
        product_id="max_energy",
        name="Max Energy",
        caffeine_mg=300,
        has_theanine=False,
        other_stimulants_mg=100,
        serving_instructions="Mix 1 scoop. Do not exceed 1 serving per day.",
        description="High-stim formula for intense workouts",
        warnings=["Contains high caffeine", "Not for caffeine-sensitive individuals"]
    ),
    ProductConfig(
        product_id="gentle_boost",
        name="Gentle Boost",
        caffeine_mg=75,
        has_theanine=True,
        other_stimulants_mg=0,
        serving_instructions="Mix 1 scoop or take 1 capsule",
        description="Mild energy for beginners or sensitive users"
    )
]

for product in DEMO_PRODUCTS:
    engine.register_product(product)


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class PersonalizeRequest(BaseModel):
    """Request body for personalization API."""
    product_id: str
    weight_kg: float
    wake_time: str
    activity_time: str
    caffeine_sensitivity: str = "normal"
    age: Optional[int] = None
    has_eaten: Optional[bool] = None
    sleep_target_time: Optional[str] = None


class PersonalizeResponse(BaseModel):
    """Response body for personalization API."""
    optimal_timing: str
    dosage_multiplier: float
    warnings: list
    expected_effects: dict
    recommendations: list
    product_name: str
    serving_instructions: str


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_brand_or_404(brand_id: str) -> BrandConfig:
    """Get brand config or raise 404."""
    if brand_id not in PRESET_BRANDS:
        raise HTTPException(status_code=404, detail=f"Brand not found: {brand_id}")
    return get_brand_config(brand_id)


def get_product_or_404(product_id: str) -> ProductConfig:
    """Get product config or raise 404."""
    try:
        return engine.get_product(product_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Product not found: {product_id}")


def build_context(
    request: Request,
    brand: BrandConfig,
    product: ProductConfig,
    **extras
) -> Dict[str, Any]:
    """Build template context with common data."""
    return {
        "request": request,
        "brand": brand.to_dict(),
        "product": {
            "id": product.product_id,
            "name": product.name,
            "description": product.description,
            "caffeine_mg": product.caffeine_mg,
            "has_theanine": product.has_theanine,
            "serving_instructions": product.serving_instructions
        },
        "css_vars": brand.to_css_vars(),
        **extras
    }


# =============================================================================
# WEB ROUTES (HTML)
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root redirect to default brand."""
    return templates.TemplateResponse(
        "landing.html",
        {
            "request": request,
            "brand": PRESET_BRANDS["modulus"].to_dict(),
            "css_vars": PRESET_BRANDS["modulus"].to_css_vars(),
            "products": [
                {"id": p.product_id, "name": p.name, "description": p.description}
                for p in DEMO_PRODUCTS
            ]
        }
    )


@app.get("/{brand_id}", response_class=HTMLResponse)
async def brand_landing(request: Request, brand_id: str):
    """Brand-specific landing page."""
    brand = get_brand_or_404(brand_id)
    
    return templates.TemplateResponse(
        "landing.html",
        {
            "request": request,
            "brand": brand.to_dict(),
            "css_vars": brand.to_css_vars(),
            "products": [
                {"id": p.product_id, "name": p.name, "description": p.description}
                for p in DEMO_PRODUCTS
            ]
        }
    )


@app.get("/{brand_id}/{product_id}", response_class=HTMLResponse)
async def product_page(request: Request, brand_id: str, product_id: str):
    """Product-specific landing page with form."""
    brand = get_brand_or_404(brand_id)
    product = get_product_or_404(product_id)
    
    return templates.TemplateResponse(
        "form.html",
        build_context(request, brand, product)
    )


@app.post("/{brand_id}/{product_id}/result", response_class=HTMLResponse)
async def show_result(
    request: Request,
    brand_id: str,
    product_id: str,
    weight_kg: float = Form(...),
    wake_time: str = Form(...),
    activity_time: str = Form(...),
    caffeine_sensitivity: str = Form("normal"),
    has_eaten: bool = Form(False),
    sleep_target_time: str = Form(None)
):
    """Show personalization results (form submission)."""
    brand = get_brand_or_404(brand_id)
    product = get_product_or_404(product_id)
    
    # Create user input
    try:
        user = UserInput(
            weight_kg=weight_kg,
            wake_time=wake_time,
            activity_time=activity_time,
            caffeine_sensitivity=caffeine_sensitivity,
            has_eaten=has_eaten if has_eaten else None,
            sleep_target_time=sleep_target_time if sleep_target_time else None
        )
    except ValueError as e:
        return templates.TemplateResponse(
            "form.html",
            build_context(request, brand, product, error=str(e))
        )
    
    # Get personalization
    result = engine.personalize(product_id, user)
    
    return templates.TemplateResponse(
        "result.html",
        build_context(
            request, 
            brand, 
            product,
            result=result.to_dict(),
            user=user.to_dict()
        )
    )


# =============================================================================
# API ROUTES (JSON)
# =============================================================================

@app.post("/api/personalize", response_model=PersonalizeResponse)
async def api_personalize(req: PersonalizeRequest):
    """
    JSON API for personalization.
    
    Fast endpoint (<100ms) for programmatic access.
    """
    # Validate product exists
    try:
        product = engine.get_product(req.product_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Product not found: {req.product_id}")
    
    # Create user input
    try:
        user = UserInput(
            weight_kg=req.weight_kg,
            wake_time=req.wake_time,
            activity_time=req.activity_time,
            caffeine_sensitivity=req.caffeine_sensitivity,
            age=req.age,
            has_eaten=req.has_eaten,
            sleep_target_time=req.sleep_target_time
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Get personalization
    result = engine.personalize(req.product_id, user)
    
    return PersonalizeResponse(
        optimal_timing=result.optimal_timing,
        dosage_multiplier=result.dosage_multiplier,
        warnings=result.warnings,
        expected_effects=result.expected_effects,
        recommendations=result.recommendations,
        product_name=product.name,
        serving_instructions=product.serving_instructions
    )


@app.get("/api/products")
async def api_list_products():
    """List all available products."""
    products = []
    for product_id in engine.list_products():
        try:
            p = engine.get_product(product_id)
            products.append({
                "id": p.product_id,
                "name": p.name,
                "description": p.description,
                "caffeine_mg": p.caffeine_mg,
                "has_theanine": p.has_theanine
            })
        except KeyError:
            pass
    
    return {"products": products}


@app.get("/api/brands")
async def api_list_brands():
    """List all available brands."""
    brands = [
        {"id": b.brand_id, "name": b.brand_name, "tagline": b.tagline}
        for b in PRESET_BRANDS.values()
    ]
    return {"brands": brands}


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "products_loaded": len(engine.list_products()),
        "brands_loaded": len(PRESET_BRANDS)
    }


# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Custom 404 handler."""
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=404,
            content={"error": "Not found", "detail": str(exc.detail)}
        )
    
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "brand": PRESET_BRANDS["modulus"].to_dict(),
            "css_vars": PRESET_BRANDS["modulus"].to_css_vars(),
            "error_code": 404,
            "error_message": "Page not found"
        },
        status_code=404
    )


@app.exception_handler(500)
async def server_error_handler(request: Request, exc: Exception):
    """Custom 500 handler."""
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"}
        )
    
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "brand": PRESET_BRANDS["modulus"].to_dict(),
            "css_vars": PRESET_BRANDS["modulus"].to_css_vars(),
            "error_code": 500,
            "error_message": "Something went wrong"
        },
        status_code=500
    )


# =============================================================================
# STARTUP
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize app on startup."""
    print(f"🚀 MODULUS Consumer App starting...")
    print(f"   Products loaded: {len(engine.list_products())}")
    print(f"   Brands loaded: {len(PRESET_BRANDS)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
