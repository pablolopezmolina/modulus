# src/api/main.py
# MODULUS — FastAPI Application V1.0
#
# Endpoints:
# - POST /simulate     → Simular un producto
# - POST /ab-test      → Comparar dos productos (misma población)
# - GET  /health       → Estado del servicio + versiones
#
# Diseño estable desde día 1 (no romper compatibilidad)

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import time
import uuid
import logging

# Engine imports
import sys

sys.path.insert(0, "..")
from core import (
    SimulationEngine,
    SimulationConfig,
    ProductComposition,
    PopulationResults,
)
from core.engine import (
    ENGINE_VERSION,
    GLUCOSE_MODEL_VERSION,
    CAFFEINE_MODEL_VERSION,
    _get_git_commit,
)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MODULUS-API")

# =============================================================================
# App Setup
# =============================================================================

app = FastAPI(
    title="MODULUS API",
    description="In-Silico Metabolic Response Simulator for Nutrition & Supplements",
    version=ENGINE_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS (para frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restringir en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Engine singleton
engine = SimulationEngine()


# =============================================================================
# Request/Response Schemas (Stable API Contract)
# =============================================================================


class ProductInput(BaseModel):
    """Composición de producto para simulación."""

    name: str = Field(..., description="Nombre del producto")
    carbohydrates_g: float = Field(0.0, ge=0, le=500, description="Carbohidratos (g)")
    glycemic_index: float = Field(70.0, ge=0, le=150, description="Índice glucémico")
    protein_g: float = Field(0.0, ge=0, le=200, description="Proteína (g)")
    fat_g: float = Field(0.0, ge=0, le=200, description="Grasa (g)")
    fiber_g: float = Field(0.0, ge=0, le=100, description="Fibra (g)")
    caffeine_mg: float = Field(0.0, ge=0, le=1000, description="Cafeína (mg)")

    # Metadata opcional
    brand: str = ""
    category: str = ""

    def to_product(self) -> ProductComposition:
        return ProductComposition(
            name=self.name,
            carbohydrates_g=self.carbohydrates_g,
            glycemic_index=self.glycemic_index,
            protein_g=self.protein_g,
            fat_g=self.fat_g,
            fiber_g=self.fiber_g,
            caffeine_mg=self.caffeine_mg,
            brand=self.brand,
            category=self.category,
        )


class SimulationRequest(BaseModel):
    """Request para simulación."""

    product: ProductInput

    # Config
    population_size: int = Field(1000, ge=10, le=10000, description="Tamaño de población")
    population_seed: Optional[int] = Field(None, description="Seed para reproducibilidad")
    duration_minutes: int = Field(240, ge=60, le=480, description="Duración (min)")

    # Subpoblación
    subpopulation: Optional[str] = Field(
        None, description="Filtro de población: 'athletes', 'prediabetic', 'elderly', etc."
    )

    # Output flags
    include_timeseries: bool = Field(False, description="Incluir curvas temporales")
    include_percentiles: bool = Field(True, description="Incluir percentiles de curvas")

    @validator("subpopulation")
    def validate_subpop(cls, v):
        valid = [None, "athletes", "prediabetic", "elderly", "young_adults", "obese"]
        if v not in valid:
            raise ValueError(f"subpopulation must be one of {valid}")
        return v


class ABTestRequest(BaseModel):
    """Request para A/B test."""

    product_a: ProductInput
    product_b: ProductInput

    population_size: int = Field(1000, ge=10, le=10000)
    population_seed: Optional[int] = None
    duration_minutes: int = Field(240, ge=60, le=480)
    subpopulation: Optional[str] = None

    include_timeseries: bool = False


class GlucoseStats(BaseModel):
    """Estadísticas de glucosa."""

    peak: Dict[str, float] = Field(default_factory=dict)
    auc: Dict[str, float] = Field(default_factory=dict)
    time_to_peak: Dict[str, float] = Field(default_factory=dict)


class CaffeineStats(BaseModel):
    """Estadísticas de cafeína."""

    peak: Dict[str, float] = Field(default_factory=dict)
    auc: Dict[str, float] = Field(default_factory=dict)
    alertness_peak: Dict[str, float] = Field(default_factory=dict)


class RiskAnalysis(BaseModel):
    """Análisis de riesgo."""

    pct_hyperglycemia: float = 0.0
    pct_severe_hyperglycemia: float = 0.0
    pct_hypoglycemia: float = 0.0
    pct_crash_risk: float = 0.0
    pct_jitter_risk: float = 0.0
    pct_sleep_risk: float = 0.0


class SimulationResponse(BaseModel):
    """Response de simulación."""

    # Metadata
    simulation_id: str
    timestamp: str
    duration_seconds: float

    # Audit
    engine_version: str
    glucose_model_version: str
    caffeine_model_version: str

    # Population
    n_individuals: int
    n_valid: int
    valid_percentage: float

    # Results
    glucose_stats: GlucoseStats
    caffeine_stats: CaffeineStats
    risk_analysis: RiskAnalysis

    # Subgroups
    subgroup_analysis: Dict[str, Any] = Field(default_factory=dict)

    # Optional curves (si include_timeseries=True)
    time_points: Optional[List[float]] = None
    glucose_percentiles: Optional[Dict[str, List[float]]] = None
    caffeine_percentiles: Optional[Dict[str, List[float]]] = None
    alertness_percentiles: Optional[Dict[str, List[float]]] = None


class ABTestResponse(BaseModel):
    """Response de A/B test."""

    simulation_id: str
    timestamp: str
    duration_seconds: float

    # Comparación
    product_a_name: str
    product_b_name: str

    # Results
    results_a: SimulationResponse
    results_b: SimulationResponse

    # Diferencias
    comparison: Dict[str, Any]


class HealthResponse(BaseModel):
    """Response de health check."""

    status: str
    timestamp: str
    engine_version: str
    glucose_model_version: str
    caffeine_model_version: str
    git_commit: Optional[str]
    adapter_config_version: str


# =============================================================================
# Helper Functions
# =============================================================================


def results_to_response(
    results: PopulationResults, include_curves: bool = False
) -> SimulationResponse:
    """Convierte PopulationResults a SimulationResponse."""

    # Construir stats
    glucose_stats = GlucoseStats(
        peak=results.glucose_stats.get("peak", {}),
        auc=results.glucose_stats.get("auc", {}),
        time_to_peak=results.glucose_stats.get("time_to_peak", {}),
    )

    caffeine_stats = CaffeineStats(
        peak=results.caffeine_stats.get("peak", {}),
        auc=results.caffeine_stats.get("auc", {}),
        alertness_peak=results.caffeine_stats.get("alertness_peak", {}),
    )

    risk = results.risk_analysis
    risk_analysis = RiskAnalysis(
        pct_hyperglycemia=risk.get("pct_hyperglycemia", 0),
        pct_severe_hyperglycemia=risk.get("pct_severe_hyperglycemia", 0),
        pct_hypoglycemia=risk.get("pct_hypoglycemia", 0),
        pct_crash_risk=risk.get("pct_crash_risk", 0),
        pct_jitter_risk=risk.get("pct_jitter_risk", 0),
        pct_sleep_risk=risk.get("pct_sleep_risk", 0),
    )

    response = SimulationResponse(
        simulation_id=results.simulation_id,
        timestamp=results.timestamp,
        duration_seconds=results.duration_seconds,
        engine_version=results.engine_version,
        glucose_model_version=results.glucose_model_version,
        caffeine_model_version=results.caffeine_model_version,
        n_individuals=results.n_individuals,
        n_valid=results.n_valid,
        valid_percentage=(
            results.n_valid / results.n_individuals * 100 if results.n_individuals > 0 else 0
        ),
        glucose_stats=glucose_stats,
        caffeine_stats=caffeine_stats,
        risk_analysis=risk_analysis,
        subgroup_analysis=results.subgroup_analysis,
    )

    # Añadir curvas si se piden
    if include_curves and results.time_points:
        response.time_points = results.time_points
        response.glucose_percentiles = results.glucose_percentiles
        response.caffeine_percentiles = results.caffeine_percentiles
        response.alertness_percentiles = results.alertness_percentiles

    return response


# =============================================================================
# Endpoints
# =============================================================================


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """
    Health check del servicio.

    Retorna versiones de todos los componentes para auditoría.
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        engine_version=ENGINE_VERSION,
        glucose_model_version=GLUCOSE_MODEL_VERSION,
        caffeine_model_version=CAFFEINE_MODEL_VERSION,
        git_commit=_get_git_commit(),
        adapter_config_version=engine.glucose_adapter.config.version,
    )


@app.post("/simulate", response_model=SimulationResponse, tags=["Simulation"])
async def simulate(request: SimulationRequest):
    """
    Simula la respuesta metabólica de una población a un producto.

    Ejecuta N simulaciones virtuales y retorna estadísticas agregadas.

    **Ejemplo de uso:**
    ```json
    {
      "product": {
        "name": "Pre-Workout X",
        "carbohydrates_g": 25,
        "glycemic_index": 85,
        "caffeine_mg": 200
      },
      "population_size": 1000,
      "subpopulation": "athletes"
    }
    ```
    """
    try:
        # Convertir request a objetos internos
        product = request.product.to_product()

        config = SimulationConfig(
            population_size=request.population_size,
            population_seed=request.population_seed,
            duration_minutes=request.duration_minutes,
            subpopulation=request.subpopulation,
            store_timeseries=request.include_timeseries,
            store_individual_results=False,  # Siempre streaming
        )

        # Ejecutar simulación
        logger.info(f"Simulating {product.name} for {config.population_size} individuals...")
        results = engine.run(product, config)

        # Convertir a response
        return results_to_response(results, include_curves=request.include_percentiles)

    except Exception as e:
        logger.error(f"Simulation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ab-test", response_model=ABTestResponse, tags=["Simulation"])
async def ab_test(request: ABTestRequest):
    """
    Ejecuta A/B test comparando dos productos con la misma población.

    Usa la MISMA población virtual para ambos productos, eliminando
    varianza por diferencias demográficas.

    **Ejemplo de uso:**
    ```json
    {
      "product_a": {"name": "Formula Original", "carbohydrates_g": 30, "caffeine_mg": 150},
      "product_b": {"name": "Formula Mejorada", "carbohydrates_g": 25, "caffeine_mg": 150, "fiber_g": 5},
      "population_size": 1000
    }
    ```
    """
    try:
        product_a = request.product_a.to_product()
        product_b = request.product_b.to_product()

        config = SimulationConfig(
            population_size=request.population_size,
            population_seed=request.population_seed,
            duration_minutes=request.duration_minutes,
            subpopulation=request.subpopulation,
            store_timeseries=request.include_timeseries,
            store_individual_results=False,
        )

        logger.info(f"A/B Test: {product_a.name} vs {product_b.name}")

        start_time = time.time()
        results_a, results_b = engine.run_ab_test(product_a, product_b, config)
        total_time = time.time() - start_time

        # Calcular comparación
        comparison = {}

        if results_a.glucose_stats.get("peak") and results_b.glucose_stats.get("peak"):
            peak_a = results_a.glucose_stats["peak"].get("mean", 0)
            peak_b = results_b.glucose_stats["peak"].get("mean", 0)
            comparison["glucose_peak_diff"] = peak_a - peak_b
            comparison["glucose_peak_diff_pct"] = (peak_a - peak_b) / peak_b * 100 if peak_b else 0

        if results_a.risk_analysis and results_b.risk_analysis:
            comparison["hyperglycemia_diff_pct"] = results_a.risk_analysis.get(
                "pct_hyperglycemia", 0
            ) - results_b.risk_analysis.get("pct_hyperglycemia", 0)

        # Determinar ganador
        if comparison.get("glucose_peak_diff", 0) < 0:
            comparison["recommendation"] = f"{product_a.name} produces lower glucose peaks"
        elif comparison.get("glucose_peak_diff", 0) > 0:
            comparison["recommendation"] = f"{product_b.name} produces lower glucose peaks"
        else:
            comparison["recommendation"] = "Products produce similar glucose responses"

        return ABTestResponse(
            simulation_id=f"ab_{results_a.simulation_id}",
            timestamp=datetime.now().isoformat(),
            duration_seconds=total_time,
            product_a_name=product_a.name,
            product_b_name=product_b.name,
            results_a=results_to_response(results_a, include_curves=request.include_timeseries),
            results_b=results_to_response(results_b, include_curves=request.include_timeseries),
            comparison=comparison,
        )

    except Exception as e:
        logger.error(f"A/B test failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/subpopulations", tags=["Reference"])
async def list_subpopulations():
    """
    Lista las subpoblaciones disponibles para filtrar.
    """
    return {
        "subpopulations": [
            {"id": "athletes", "description": "Active individuals with high insulin sensitivity"},
            {
                "id": "prediabetic",
                "description": "Elevated fasting glucose, reduced insulin sensitivity",
            },
            {"id": "elderly", "description": "Age 60+, slower caffeine metabolism"},
            {"id": "young_adults", "description": "Age 18-29"},
            {"id": "obese", "description": "BMI >= 30"},
        ]
    }


# =============================================================================
# Run (for development)
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
