# src/core/engine.py
# MODULUS — Simulation Engine V3.3 (Production-Ready)
#
# Orquesta simulaciones masivas combinando:
# - Población virtual (PopulationGenerator)
# - Modelos fisiológicos REALES (DallaManModel, EliteCaffeineModel)
# - Composición de producto (ProductComposition)
#
# V3.3: Streaming real, audit-grade metadata, defaults producción
#
# Changelog:
# - V3.0: Integración ODEs reales
# - V3.1: Adaptadores centralizados, A/B testing
# - V3.2: Versionado supuestos, tests fisiológicos
# - V3.3: Streaming aggregation, audit metadata, defaults producción

import hashlib
import json
import logging
import os
import subprocess
import time
import warnings
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Callable, Dict, Generator, List, Literal, Optional, Tuple

import numpy as np

# Imports internos
from .population import PopulationGenerator, GenerationConfig, VirtualPerson
from .models import (
    DallaManModel,
    DallaManParams,
    GlucoseInput,
    EliteCaffeineModel,
    CaffeineParams,
    CaffeineInput,
)
from .adapters import (
    GlucoseModelAdapter,
    CaffeineModelAdapter,
    MealEffectConfig,
    create_adapters,
)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MODULUS-ENGINE")

# Engine version
ENGINE_VERSION = "3.3.0"
GLUCOSE_MODEL_VERSION = "DallaMan2007-v1.0"
CAFFEINE_MODEL_VERSION = "Blanchard1983-v1.0"


def _get_git_commit() -> Optional[str]:
    """Intenta obtener el commit hash actual de git."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


# =============================================================================
# Streaming Aggregator (memoria O(1) en lugar de O(N))
# =============================================================================


class StreamingAggregator:
    """
    Agrega resultados de simulación on-the-fly sin acumular en memoria.

    Usa algoritmo de Welford para calcular media y varianza en un solo paso.
    Mantiene contadores de riesgo y subgrupos sin guardar resultados individuales.

    Memory: O(n_metrics + n_subgroups) en lugar de O(N_individuals)
    """

    def __init__(self, config: "SimulationConfig"):
        self.config = config
        self.n_total = 0
        self.n_valid = 0

        # Welford's online algorithm para media y varianza
        self._glucose_peak = WelfordAccumulator()
        self._glucose_auc = WelfordAccumulator()
        self._glucose_ttp = WelfordAccumulator()
        self._caffeine_peak = WelfordAccumulator()
        self._caffeine_auc = WelfordAccumulator()
        self._alertness_peak = WelfordAccumulator()

        # Risk counters
        self._risk_counts = {
            "hyperglycemia": 0,
            "severe_hyperglycemia": 0,
            "hypoglycemia": 0,
            "crash_risk": 0,
            "jitter_risk": 0,
            "sleep_risk": 0,
        }

        # Subgroup counters: {category: {metric: WelfordAccumulator}}
        self._bmi_groups: Dict[str, Dict[str, Any]] = {}
        self._age_groups: Dict[str, Dict[str, Any]] = {}
        self._activity_groups: Dict[str, Dict[str, Any]] = {}

        # Sample storage para percentiles de curvas (limitado)
        self._curve_samples: List[Dict[str, np.ndarray]] = []
        self._sample_indices: List[int] = []

        # Stored individual results (solo si config.store_individual_results)
        self._individual_results: List["IndividualResult"] = []

    def update(self, person: "VirtualPerson", result: "IndividualResult") -> None:
        """Actualiza agregados con un nuevo resultado."""
        self.n_total += 1

        if not result.valid:
            return

        self.n_valid += 1

        # Actualizar estadísticas escalares
        if result.peak_glucose > 0:
            self._glucose_peak.update(result.peak_glucose)
        if result.auc_glucose > 0:
            self._glucose_auc.update(result.auc_glucose)
        if result.time_to_peak_glucose > 0:
            self._glucose_ttp.update(result.time_to_peak_glucose)
        if result.peak_caffeine > 0:
            self._caffeine_peak.update(result.peak_caffeine)
        if result.auc_caffeine > 0:
            self._caffeine_auc.update(result.auc_caffeine)
        if result.alertness_peak > 0:
            self._alertness_peak.update(result.alertness_peak)

        # Actualizar contadores de riesgo
        if result.hyperglycemia_flag:
            self._risk_counts["hyperglycemia"] += 1
        if result.severe_hyperglycemia_flag:
            self._risk_counts["severe_hyperglycemia"] += 1
        if result.hypoglycemia_flag:
            self._risk_counts["hypoglycemia"] += 1
        if result.crash_risk_flag:
            self._risk_counts["crash_risk"] += 1
        if result.jitter_risk_flag:
            self._risk_counts["jitter_risk"] += 1
        if result.sleep_risk_flag:
            self._risk_counts["sleep_risk"] += 1

        # Actualizar subgrupos
        self._update_subgroup(self._bmi_groups, person.bmi_category, result)
        self._update_subgroup(self._age_groups, self._age_group(person.age), result)
        self._update_subgroup(self._activity_groups, person.activity_level, result)

        # Sample curvas para percentiles (reservoir sampling)
        if self.config.store_timeseries and result.glucose_curve is not None:
            self._sample_curve(result)

        # Guardar resultado individual si se pide
        if self.config.store_individual_results:
            self._individual_results.append(result)

    def _update_subgroup(
        self, groups: Dict[str, Dict[str, Any]], key: str, result: "IndividualResult"
    ) -> None:
        """Actualiza estadísticas de un subgrupo."""
        if key not in groups:
            groups[key] = {
                "n": 0,
                "hyperglycemia": 0,
                "crash_risk": 0,
                "glucose_peak": WelfordAccumulator(),
                "alertness_peak": WelfordAccumulator(),
            }

        g = groups[key]
        g["n"] += 1
        if result.hyperglycemia_flag:
            g["hyperglycemia"] += 1
        if result.crash_risk_flag:
            g["crash_risk"] += 1
        if result.peak_glucose > 0:
            g["glucose_peak"].update(result.peak_glucose)
        if result.alertness_peak > 0:
            g["alertness_peak"].update(result.alertness_peak)

    def _age_group(self, age: int) -> str:
        if age < 30:
            return "18-29"
        elif age < 45:
            return "30-44"
        elif age < 60:
            return "45-59"
        else:
            return "60+"

    def _sample_curve(self, result: "IndividualResult") -> None:
        """Reservoir sampling para curvas (mantiene máximo sample_size)."""
        max_samples = self.config.percentile_sample_size

        if len(self._curve_samples) < max_samples:
            self._curve_samples.append(
                {
                    "glucose": np.array(result.glucose_curve) if result.glucose_curve else None,
                    "caffeine": np.array(result.caffeine_curve) if result.caffeine_curve else None,
                    "alertness": (
                        np.array(result.alertness_curve) if result.alertness_curve else None
                    ),
                }
            )
        else:
            # Reservoir sampling: reemplazar con probabilidad max_samples/n
            j = np.random.randint(0, self.n_valid)
            if j < max_samples:
                self._curve_samples[j] = {
                    "glucose": np.array(result.glucose_curve) if result.glucose_curve else None,
                    "caffeine": np.array(result.caffeine_curve) if result.caffeine_curve else None,
                    "alertness": (
                        np.array(result.alertness_curve) if result.alertness_curve else None
                    ),
                }

    def get_glucose_stats(self) -> Dict[str, Dict[str, float]]:
        return {
            "peak": self._glucose_peak.get_stats(),
            "auc": self._glucose_auc.get_stats(),
            "time_to_peak": self._glucose_ttp.get_stats(),
        }

    def get_caffeine_stats(self) -> Dict[str, Dict[str, float]]:
        return {
            "peak": self._caffeine_peak.get_stats(),
            "auc": self._caffeine_auc.get_stats(),
            "alertness_peak": self._alertness_peak.get_stats(),
        }

    def get_risk_analysis(self) -> Dict[str, float]:
        if self.n_valid == 0:
            return {f"pct_{k}": 0.0 for k in self._risk_counts}
        return {f"pct_{k}": v / self.n_valid * 100 for k, v in self._risk_counts.items()}

    def get_subgroup_analysis(self) -> Dict[str, Dict[str, Any]]:
        def format_group(groups: Dict) -> Dict[str, Dict[str, float]]:
            result = {}
            for key, g in groups.items():
                n = g["n"]
                if n > 0:
                    result[key] = {
                        "n": n,
                        "pct_hyperglycemia": g["hyperglycemia"] / n * 100,
                        "pct_crash_risk": g["crash_risk"] / n * 100,
                        "avg_peak_glucose": (
                            g["glucose_peak"].mean if g["glucose_peak"].n > 0 else 0
                        ),
                        "avg_alertness": (
                            g["alertness_peak"].mean if g["alertness_peak"].n > 0 else 0
                        ),
                    }
            return result

        return {
            "by_bmi": format_group(self._bmi_groups),
            "by_age": format_group(self._age_groups),
            "by_activity": format_group(self._activity_groups),
        }

    def get_curve_percentiles(self, time_points: List[float]) -> Tuple[Dict, Dict, Dict]:
        """Calcula percentiles de curvas desde las muestras."""
        glucose_pct = {}
        caffeine_pct = {}
        alertness_pct = {}

        if not self._curve_samples or not time_points:
            return glucose_pct, caffeine_pct, alertness_pct

        n_points = len(time_points)

        # Filtrar muestras válidas de glucosa
        glucose_curves = [
            s["glucose"]
            for s in self._curve_samples
            if s["glucose"] is not None and len(s["glucose"]) == n_points
        ]
        if glucose_curves:
            matrix = np.array(glucose_curves)
            glucose_pct = self._calc_percentiles(matrix)

        # Cafeína
        caffeine_curves = [
            s["caffeine"]
            for s in self._curve_samples
            if s["caffeine"] is not None and len(s["caffeine"]) == n_points
        ]
        if caffeine_curves:
            matrix = np.array(caffeine_curves)
            caffeine_pct = self._calc_percentiles(matrix)

        # Alertness
        alertness_curves = [
            s["alertness"]
            for s in self._curve_samples
            if s["alertness"] is not None and len(s["alertness"]) == n_points
        ]
        if alertness_curves:
            matrix = np.array(alertness_curves)
            alertness_pct = self._calc_percentiles(matrix)

        return glucose_pct, caffeine_pct, alertness_pct

    def _calc_percentiles(self, matrix: np.ndarray) -> Dict[str, List[float]]:
        if len(matrix) == 0:
            return {}
        return {
            "p05": np.percentile(matrix, 5, axis=0).tolist(),
            "p25": np.percentile(matrix, 25, axis=0).tolist(),
            "p50": np.percentile(matrix, 50, axis=0).tolist(),
            "p75": np.percentile(matrix, 75, axis=0).tolist(),
            "p95": np.percentile(matrix, 95, axis=0).tolist(),
            "mean": np.mean(matrix, axis=0).tolist(),
        }


class WelfordAccumulator:
    """
    Algoritmo de Welford para calcular media y varianza en un solo paso.
    Numéricamente estable, O(1) memoria.
    """

    def __init__(self):
        self.n = 0
        self.mean = 0.0
        self.M2 = 0.0  # Sum of squares of differences from mean
        self._min = float("inf")
        self._max = float("-inf")
        self._values_for_percentiles: List[float] = []  # Solo si n < 1000

    def update(self, x: float) -> None:
        self.n += 1
        delta = x - self.mean
        self.mean += delta / self.n
        delta2 = x - self.mean
        self.M2 += delta * delta2

        self._min = min(self._min, x)
        self._max = max(self._max, x)

        # Guardar valores para percentiles solo si pocos
        if self.n <= 1000:
            self._values_for_percentiles.append(x)

    @property
    def variance(self) -> float:
        if self.n < 2:
            return 0.0
        return self.M2 / (self.n - 1)

    @property
    def std(self) -> float:
        return np.sqrt(self.variance)

    def get_stats(self) -> Dict[str, float]:
        if self.n == 0:
            return {}

        stats = {
            "mean": self.mean,
            "std": self.std,
            "min": self._min if self._min != float("inf") else 0,
            "max": self._max if self._max != float("-inf") else 0,
        }

        # Percentiles si tenemos valores
        if self._values_for_percentiles:
            arr = np.array(self._values_for_percentiles)
            stats["p10"] = float(np.percentile(arr, 10))
            stats["p50"] = float(np.percentile(arr, 50))
            stats["p90"] = float(np.percentile(arr, 90))

        return stats


# =============================================================================
# Product Input
# =============================================================================


@dataclass
class ProductComposition:
    """
    Composición de un producto nutricional/suplemento.

    Attributes:
        name: Nombre del producto
        carbohydrates_g: Carbohidratos totales (g)
        glycemic_index: Índice glucémico (0-100)
        protein_g: Proteína (g) - ralentiza absorción
        fat_g: Grasa (g) - ralentiza absorción
        fiber_g: Fibra (g) - ralentiza absorción
        caffeine_mg: Cafeína total (mg)
        serving_size_g: Tamaño de porción (g)
    """

    name: str
    carbohydrates_g: float = 0.0
    glycemic_index: float = 70.0
    protein_g: float = 0.0
    fat_g: float = 0.0
    fiber_g: float = 0.0
    caffeine_mg: float = 0.0
    serving_size_g: float = 100.0

    # Metadata
    brand: str = ""
    category: str = ""

    def get_product_hash(self) -> str:
        """Hash único basado en composición."""
        data = {
            "carbs": round(self.carbohydrates_g, 1),
            "gi": round(self.glycemic_index, 1),
            "protein": round(self.protein_g, 1),
            "fat": round(self.fat_g, 1),
            "fiber": round(self.fiber_g, 1),
            "caffeine": round(self.caffeine_mg, 1),
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:12]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =============================================================================
# Simulation Configuration
# =============================================================================


@dataclass
class SimulationConfig:
    """
    Configuración de una simulación.

    DEFAULTS optimizados para PRODUCCIÓN (memoria eficiente):
    - store_timeseries=False (no guardar curvas completas)
    - store_individual_results=False (no guardar resultados por individuo)

    Para DEBUG/análisis, activar explícitamente:
        config = SimulationConfig(store_timeseries=True, store_individual_results=True)
    """

    population_size: int = 1000
    population_seed: Optional[int] = 42
    simulation_seed: Optional[int] = 42

    # Tiempo
    duration_minutes: int = 240
    time_step_minutes: float = 1.0

    # Población
    subpopulation: Optional[str] = None
    bmi_range: Optional[Tuple[float, float]] = None
    age_range: Optional[Tuple[int, int]] = None

    # Ejecución
    parallel: bool = False  # Por ahora secuencial
    n_workers: int = 4

    # Storage flags - DEFAULTS DE PRODUCCIÓN (memoria eficiente)
    store_timeseries: bool = False  # Default False: no guardar curvas
    store_individual_results: bool = False  # Default False: streaming mode

    # Percentiles de curvas (solo si store_timeseries=True)
    # Si False y se necesitan percentiles, usa sampling
    compute_curve_percentiles: bool = True
    percentile_sample_size: int = 200  # Máximo de curvas para percentiles

    def get_config_hash(self) -> str:
        data = {
            "pop_size": self.population_size,
            "pop_seed": self.population_seed,
            "sim_seed": self.simulation_seed,
            "duration": self.duration_minutes,
            "dt": self.time_step_minutes,
            "subpop": self.subpopulation,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:12]


# =============================================================================
# Result Containers
# =============================================================================


@dataclass
class IndividualResult:
    """Resultado de simulación para un individuo."""

    person_id: str
    valid: bool

    # Métricas de glucosa
    peak_glucose: float = 0.0
    min_glucose: float = 0.0
    auc_glucose: float = 0.0
    time_to_peak_glucose: float = 0.0
    final_glucose: float = 0.0

    # Métricas de cafeína
    peak_caffeine: float = 0.0
    time_to_peak_caffeine: float = 0.0
    auc_caffeine: float = 0.0
    alertness_peak: float = 0.0

    # Flags de riesgo
    hyperglycemia_flag: bool = False  # > 140 mg/dL
    severe_hyperglycemia_flag: bool = False  # > 180 mg/dL
    hypoglycemia_flag: bool = False  # < 70 mg/dL
    crash_risk_flag: bool = False  # Caída >30 mg/dL
    jitter_risk_flag: bool = False  # Cafeína > 9 mg/L
    sleep_risk_flag: bool = False  # Cafeína > 2 mg/L a las 8h

    # Timeseries (opcional)
    time_points: Optional[List[float]] = None
    glucose_curve: Optional[List[float]] = None
    caffeine_curve: Optional[List[float]] = None
    alertness_curve: Optional[List[float]] = None

    # Debug info
    glucose_valid: bool = True
    caffeine_valid: bool = True
    error_message: str = ""


@dataclass
class PopulationResults:
    """Resultados agregados de simulación poblacional."""

    # Metadata
    simulation_id: str
    product: Dict[str, Any]
    config: Dict[str, Any]
    timestamp: str
    duration_seconds: float

    # === AUDIT-GRADE TRACEABILITY ===
    engine_version: str = ENGINE_VERSION
    glucose_model_version: str = GLUCOSE_MODEL_VERSION
    caffeine_model_version: str = CAFFEINE_MODEL_VERSION
    adapter_config: Dict[str, Any] = field(default_factory=dict)
    git_commit: Optional[str] = None
    seeds: Dict[str, Optional[int]] = field(default_factory=dict)

    # Population
    n_individuals: int = 0
    n_valid: int = 0
    population_summary: Dict[str, Any] = field(default_factory=dict)

    # Curvas percentiles (para gráficos)
    time_points: List[float] = field(default_factory=list)
    glucose_percentiles: Dict[str, List[float]] = field(default_factory=dict)
    caffeine_percentiles: Dict[str, List[float]] = field(default_factory=dict)
    alertness_percentiles: Dict[str, List[float]] = field(default_factory=dict)

    # Estadísticas escalares
    glucose_stats: Dict[str, Dict[str, float]] = field(default_factory=dict)
    caffeine_stats: Dict[str, Dict[str, float]] = field(default_factory=dict)

    # Risk Assessment
    risk_analysis: Dict[str, float] = field(default_factory=dict)

    # Subgroup Analysis
    subgroup_analysis: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Individual results (opcional - vacío si store_individual_results=False)
    individual_results: List[IndividualResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serializa a diccionario con toda la metadata de auditoría."""
        return {
            # Audit metadata (primero para visibilidad)
            "audit": {
                "simulation_id": self.simulation_id,
                "timestamp": self.timestamp,
                "engine_version": self.engine_version,
                "glucose_model_version": self.glucose_model_version,
                "caffeine_model_version": self.caffeine_model_version,
                "git_commit": self.git_commit,
                "seeds": self.seeds,
                "adapter_config": self.adapter_config,
            },
            # Input
            "product": self.product,
            "config": self.config,
            # Results
            "duration_seconds": self.duration_seconds,
            "n_individuals": self.n_individuals,
            "n_valid": self.n_valid,
            "population_summary": self.population_summary,
            "time_points": self.time_points,
            "glucose_percentiles": self.glucose_percentiles,
            "caffeine_percentiles": self.caffeine_percentiles,
            "alertness_percentiles": self.alertness_percentiles,
            "glucose_stats": self.glucose_stats,
            "caffeine_stats": self.caffeine_stats,
            "risk_analysis": self.risk_analysis,
            "subgroup_analysis": self.subgroup_analysis,
        }

    def to_json(self, path: str) -> None:
        """Guarda a archivo JSON."""
        import json

        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)


# =============================================================================
# Simulation Engine
# =============================================================================


class SimulationEngine:
    """
    Motor principal de simulación MODULUS.

    Orquesta:
    1. Generación de población virtual
    2. Ejecución de simulaciones con modelos fisiológicos REALES
    3. Agregación de resultados y análisis de riesgo

    Features V3.1:
    - Adaptadores centralizados (no doble conteo)
    - A/B testing con misma población
    - Modo sin timeseries para N grande

    Usage:
        engine = SimulationEngine()

        # Simulación simple
        results = engine.run(product, config)

        # A/B Testing (misma población)
        results_a, results_b = engine.run_ab_test(product_a, product_b, config)
    """

    def __init__(self, meal_config: Optional[MealEffectConfig] = None):
        """
        Inicializa el engine.

        Args:
            meal_config: Configuración de efectos de comida. Si None, usa defaults.
        """
        self.population_generator = PopulationGenerator()
        self.glucose_adapter, self.caffeine_adapter = create_adapters(meal_config)

    def run(
        self,
        product: ProductComposition,
        config: Optional[SimulationConfig] = None,
        population: Optional[List[VirtualPerson]] = None,
    ) -> PopulationResults:
        """
        Ejecuta simulación completa.

        Args:
            product: Composición del producto
            config: Configuración de simulación
            population: Población pre-generada (para A/B testing). Si None, genera nueva.

        Returns:
            PopulationResults con estadísticas agregadas
        """
        if config is None:
            config = SimulationConfig()

        start_time = time.time()

        # 1. Generar o usar población existente
        if population is None:
            logger.info(
                f"🔬 Generating population: n={config.population_size}, subpop={config.subpopulation}"
            )
            population = self._generate_population(config)
        else:
            logger.info(f"🔬 Using provided population: n={len(population)}")

        # 2. Ejecutar simulaciones con STREAMING AGGREGATION
        logger.info(f"⚡ Running {len(population)} simulations (streaming mode)...")
        aggregator = StreamingAggregator(config)

        # Simular y agregar on-the-fly (memoria O(1) por individuo)
        for i, person in enumerate(population):
            if (i + 1) % 100 == 0:
                logger.info(f"  Progress: {i+1}/{len(population)}")

            result = self._simulate_individual(person, product, config)
            aggregator.update(person, result)
            # result se descarta aquí si no se guarda (liberando memoria)

        # 3. Construir resultados desde aggregator
        logger.info("📊 Building results...")
        results = self._build_results_from_aggregator(
            aggregator, population, product, config, start_time
        )

        elapsed = time.time() - start_time
        valid_pct = (
            results.n_valid / results.n_individuals * 100 if results.n_individuals > 0 else 0
        )
        logger.info(
            f"✅ Complete in {elapsed:.1f}s ({results.n_valid}/{results.n_individuals} valid, {valid_pct:.1f}%)"
        )

        return results

    def run_ab_test(
        self,
        product_a: ProductComposition,
        product_b: ProductComposition,
        config: Optional[SimulationConfig] = None,
    ) -> Tuple[PopulationResults, PopulationResults]:
        """
        Ejecuta A/B test con la MISMA población para ambos productos.

        Esto elimina varianza por diferencias poblacionales y permite
        comparación directa individuo-a-individuo.

        Args:
            product_a: Primer producto
            product_b: Segundo producto
            config: Configuración de simulación

        Returns:
            Tuple de (results_a, results_b)
        """
        if config is None:
            config = SimulationConfig()

        logger.info("=" * 60)
        logger.info(f"🔬 A/B TEST: {product_a.name} vs {product_b.name}")
        logger.info("=" * 60)

        # Generar población UNA VEZ
        logger.info(f"Generating shared population: n={config.population_size}")
        population = self._generate_population(config)

        # Correr producto A
        logger.info(f"\n--- Product A: {product_a.name} ---")
        results_a = self.run(product_a, config, population=population)

        # Correr producto B con MISMA población
        logger.info(f"\n--- Product B: {product_b.name} ---")
        results_b = self.run(product_b, config, population=population)

        # Log comparación rápida
        logger.info("\n--- COMPARISON ---")
        if results_a.glucose_stats.get("peak") and results_b.glucose_stats.get("peak"):
            diff = results_a.glucose_stats["peak"]["mean"] - results_b.glucose_stats["peak"]["mean"]
            logger.info(f"Glucose Peak Δ: {diff:+.1f} mg/dL (A-B)")

        return results_a, results_b

    def generate_population(
        self,
        config: Optional[SimulationConfig] = None,
    ) -> List[VirtualPerson]:
        """
        Genera población para uso externo (ej. múltiples tests).

        Returns:
            Lista de VirtualPerson
        """
        if config is None:
            config = SimulationConfig()
        return self._generate_population(config)

    # =========================================================================
    # Population Generation
    # =========================================================================

    def _generate_population(self, config: SimulationConfig) -> List[VirtualPerson]:
        """Genera población virtual."""
        gen_config = GenerationConfig(
            n_individuals=config.population_size,
            seed=config.population_seed,
            subpopulation=config.subpopulation,
            bmi_range=config.bmi_range,
            age_range=config.age_range,
        )
        return self.population_generator.generate(config=gen_config)

    # =========================================================================
    # Simulation Execution (with REAL models)
    # =========================================================================

    def _run_simulations(
        self,
        population: List[VirtualPerson],
        product: ProductComposition,
        config: SimulationConfig,
    ) -> List[IndividualResult]:
        """Ejecuta simulación para cada individuo usando modelos REALES."""
        results = []

        for i, person in enumerate(population):
            if (i + 1) % 100 == 0:
                logger.info(f"  Progress: {i+1}/{len(population)}")

            result = self._simulate_individual(person, product, config)
            results.append(result)

        return results

    def _simulate_individual(
        self,
        person: VirtualPerson,
        product: ProductComposition,
        config: SimulationConfig,
    ) -> IndividualResult:
        """
        Simula respuesta de un individuo usando modelos fisiológicos REALES.
        """
        result = IndividualResult(person_id=person.person_id, valid=True)

        glucose_curve = None
        caffeine_curve = None
        alertness_curve = None
        time_points = None

        # === 1. MODELO GLUCOSA (Dalla Man REAL) ===
        if product.carbohydrates_g > 0:
            try:
                g_result = self._run_glucose_model(person, product, config)

                if g_result["valid"]:
                    time_points = g_result["time_points"]
                    glucose_curve = g_result["glucose"]

                    result.peak_glucose = g_result["peak"]
                    result.min_glucose = g_result["min"]
                    result.time_to_peak_glucose = g_result["time_to_peak"]
                    result.auc_glucose = g_result["auc"]
                    result.final_glucose = g_result["final"]

                    # Risk flags
                    result.hyperglycemia_flag = result.peak_glucose > 140
                    result.severe_hyperglycemia_flag = result.peak_glucose > 180
                    result.hypoglycemia_flag = result.min_glucose < 70

                    # Crash risk: glucose drops >30 below baseline after peak
                    baseline = person.fasting_glucose_mg_dl
                    if glucose_curve is not None:
                        peak_idx = int(np.argmax(glucose_curve))
                        if peak_idx < len(glucose_curve) - 1:
                            min_after_peak = np.min(glucose_curve[peak_idx:])
                            result.crash_risk_flag = (baseline - min_after_peak) > 30
                else:
                    result.glucose_valid = False
                    result.error_message += f"Glucose: {g_result.get('error', 'unknown')}; "

            except Exception as e:
                result.glucose_valid = False
                result.error_message += f"Glucose exception: {str(e)}; "

        # === 2. MODELO CAFEÍNA (PK REAL) ===
        if product.caffeine_mg > 0:
            try:
                c_result = self._run_caffeine_model(person, product, config)

                if c_result["valid"]:
                    if time_points is None:
                        time_points = c_result["time_points"]
                    caffeine_curve = c_result["caffeine"]
                    alertness_curve = c_result["alertness"]

                    result.peak_caffeine = c_result["peak"]
                    result.time_to_peak_caffeine = c_result["time_to_peak"]
                    result.auc_caffeine = c_result["auc"]
                    result.alertness_peak = c_result["alertness_peak"]

                    # Risk flags
                    result.jitter_risk_flag = result.peak_caffeine > 9.0

                    # Sleep risk: caffeine > 2 mg/L at end of simulation (or 8h)
                    if caffeine_curve is not None and len(caffeine_curve) > 0:
                        # Check at 8 hours (480 min) or end
                        idx_8h = min(int(480 / config.time_step_minutes), len(caffeine_curve) - 1)
                        result.sleep_risk_flag = caffeine_curve[idx_8h] > 2.0
                else:
                    result.caffeine_valid = False
                    result.error_message += f"Caffeine: {c_result.get('error', 'unknown')}; "

            except Exception as e:
                result.caffeine_valid = False
                result.error_message += f"Caffeine exception: {str(e)}; "

        # Validez global
        result.valid = result.glucose_valid and result.caffeine_valid

        # Store timeseries if requested
        if config.store_timeseries and time_points is not None:
            result.time_points = (
                time_points.tolist() if isinstance(time_points, np.ndarray) else time_points
            )
            if glucose_curve is not None:
                result.glucose_curve = (
                    glucose_curve.tolist()
                    if isinstance(glucose_curve, np.ndarray)
                    else glucose_curve
                )
            if caffeine_curve is not None:
                result.caffeine_curve = (
                    caffeine_curve.tolist()
                    if isinstance(caffeine_curve, np.ndarray)
                    else caffeine_curve
                )
            if alertness_curve is not None:
                result.alertness_curve = (
                    alertness_curve.tolist()
                    if isinstance(alertness_curve, np.ndarray)
                    else alertness_curve
                )

        return result

    def _run_glucose_model(
        self,
        person: VirtualPerson,
        product: ProductComposition,
        config: SimulationConfig,
    ) -> Dict[str, Any]:
        """
        Ejecuta modelo Dalla Man REAL para glucosa.

        Usa GlucoseModelAdapter para centralizar lógica de mapping
        y evitar doble conteo de efectos.
        """
        # Crear modelo con parámetros base
        model = DallaManModel(params=DallaManParams())

        # Obtener overrides via adaptador (combina persona + producto)
        overrides = self.glucose_adapter.get_param_overrides(product, person)

        # Aplicar overrides al modelo
        for key, value in overrides.items():
            if hasattr(model.p, key):
                setattr(model.p, key, value)

        # Recalibrar con nuevos parámetros
        try:
            model.recalibrate()
        except Exception as e:
            return {"valid": False, "error": f"Calibration failed: {str(e)}"}

        # Crear input via adaptador
        glucose_input = self.glucose_adapter.create_input(
            product,
            person,
            duration_minutes=float(config.duration_minutes),
            time_step_minutes=float(config.time_step_minutes),
        )

        # Simular
        sim_result = model.simulate(glucose_input)

        # Extraer resultados
        if not sim_result.metadata.get("is_sim_valid", False):
            return {
                "valid": False,
                "error": sim_result.metadata.get("solver_message", "Simulation invalid"),
            }

        glucose = sim_result.channels.get("plasma_glucose", np.array([]))

        if len(glucose) == 0:
            return {"valid": False, "error": "Empty glucose curve"}

        return {
            "valid": True,
            "time_points": sim_result.time_points,
            "glucose": glucose,
            "peak": float(np.max(glucose)),
            "min": float(np.min(glucose)),
            "time_to_peak": float(sim_result.time_points[np.argmax(glucose)]),
            "auc": float(sim_result.metrics.get("auc_glucose", 0)),
            "final": float(glucose[-1]),
        }

    def _run_caffeine_model(
        self,
        person: VirtualPerson,
        product: ProductComposition,
        config: SimulationConfig,
    ) -> Dict[str, Any]:
        """
        Ejecuta modelo de cafeína PK REAL.

        Usa CaffeineModelAdapter para centralizar lógica.
        """
        # Crear modelo con parámetros base
        model = EliteCaffeineModel(params=CaffeineParams())

        # Obtener overrides via adaptador
        overrides = self.caffeine_adapter.get_param_overrides(product, person)

        # Aplicar overrides
        for key, value in overrides.items():
            if hasattr(model.p, key):
                setattr(model.p, key, value)

        # Crear input via adaptador
        caffeine_input = self.caffeine_adapter.create_input(
            product,
            person,
            duration_minutes=float(config.duration_minutes),
            time_step_minutes=float(config.time_step_minutes),
        )

        # Simular
        sim_result = model.simulate(caffeine_input)

        # Extraer resultados
        if not sim_result.metadata.get("is_sim_valid", False):
            return {
                "valid": False,
                "error": sim_result.metadata.get("solver_message", "Simulation invalid"),
            }

        caffeine = sim_result.channels.get("plasma_caffeine", np.array([]))
        alertness = sim_result.channels.get("alertness_score", np.array([]))

        if len(caffeine) == 0:
            return {"valid": False, "error": "Empty caffeine curve"}

        return {
            "valid": True,
            "time_points": sim_result.time_points,
            "caffeine": caffeine,
            "alertness": alertness,
            "peak": float(np.max(caffeine)),
            "time_to_peak": float(sim_result.metrics.get("Tmax", 0)),
            "auc": float(sim_result.metrics.get("AUC", 0)),
            "alertness_peak": float(np.max(alertness)) if len(alertness) > 0 else 0,
        }

    # =========================================================================
    # Results Aggregation
    # =========================================================================

    def _build_results_from_aggregator(
        self,
        aggregator: StreamingAggregator,
        population: List[VirtualPerson],
        product: ProductComposition,
        config: SimulationConfig,
        start_time: float,
    ) -> PopulationResults:
        """
        Construye PopulationResults desde StreamingAggregator.

        Este método NO itera sobre resultados individuales (ya procesados
        y descartados durante streaming).
        """
        sim_id = f"{product.get_product_hash()}_{config.get_config_hash()}_{int(time.time())}"

        # Population summary
        pop_summary = self.population_generator.get_population_summary(population)

        # Time points (necesitamos uno de referencia para percentiles)
        time_points = list(
            np.arange(
                0, config.duration_minutes + config.time_step_minutes, config.time_step_minutes
            )
        )

        # Percentiles de curvas (desde muestras del aggregator)
        glucose_pct, caffeine_pct, alertness_pct = aggregator.get_curve_percentiles(time_points)

        return PopulationResults(
            simulation_id=sim_id,
            product=product.to_dict(),
            config=asdict(config),
            timestamp=datetime.now().isoformat(),
            duration_seconds=time.time() - start_time,
            # Audit metadata
            engine_version=ENGINE_VERSION,
            glucose_model_version=GLUCOSE_MODEL_VERSION,
            caffeine_model_version=CAFFEINE_MODEL_VERSION,
            adapter_config=self.glucose_adapter.config.to_dict(),
            git_commit=_get_git_commit(),
            seeds={
                "population_seed": config.population_seed,
                "simulation_seed": config.simulation_seed,
            },
            # Population
            n_individuals=aggregator.n_total,
            n_valid=aggregator.n_valid,
            population_summary=pop_summary,
            # Curves
            time_points=time_points if config.store_timeseries else [],
            glucose_percentiles=glucose_pct,
            caffeine_percentiles=caffeine_pct,
            alertness_percentiles=alertness_pct,
            # Stats (from Welford accumulators)
            glucose_stats=aggregator.get_glucose_stats(),
            caffeine_stats=aggregator.get_caffeine_stats(),
            # Risk
            risk_analysis=aggregator.get_risk_analysis(),
            # Subgroups
            subgroup_analysis=aggregator.get_subgroup_analysis(),
            # Individual results (solo si se pidieron)
            individual_results=aggregator._individual_results,
        )

    def _aggregate_results(
        self,
        population: List[VirtualPerson],
        individual_results: List[IndividualResult],
        product: ProductComposition,
        config: SimulationConfig,
        start_time: float,
    ) -> PopulationResults:
        """Agrega resultados individuales en estadísticas poblacionales."""

        sim_id = f"{product.get_product_hash()}_{config.get_config_hash()}_{int(time.time())}"

        # Filtrar válidos
        valid_results = [r for r in individual_results if r.valid]
        n_valid = len(valid_results)
        n_total = len(individual_results)

        if n_valid == 0:
            warnings.warn("No valid simulations!")
            return self._create_empty_results(product, config, start_time, population)

        # Population summary
        pop_summary = self.population_generator.get_population_summary(population)

        # Extraer time_points del primer resultado válido
        time_points = valid_results[0].time_points or []

        # Matrices para percentiles
        has_glucose = any(r.glucose_curve is not None for r in valid_results)
        has_caffeine = any(r.caffeine_curve is not None for r in valid_results)

        glucose_percentiles = {}
        caffeine_percentiles = {}
        alertness_percentiles = {}

        if has_glucose and time_points:
            glucose_matrix = np.array(
                [
                    r.glucose_curve
                    for r in valid_results
                    if r.glucose_curve is not None and len(r.glucose_curve) == len(time_points)
                ]
            )
            if len(glucose_matrix) > 0:
                glucose_percentiles = self._calc_percentiles(glucose_matrix)

        if has_caffeine and time_points:
            caffeine_matrix = np.array(
                [
                    r.caffeine_curve
                    for r in valid_results
                    if r.caffeine_curve is not None and len(r.caffeine_curve) == len(time_points)
                ]
            )
            alertness_matrix = np.array(
                [
                    r.alertness_curve
                    for r in valid_results
                    if r.alertness_curve is not None and len(r.alertness_curve) == len(time_points)
                ]
            )
            if len(caffeine_matrix) > 0:
                caffeine_percentiles = self._calc_percentiles(caffeine_matrix)
            if len(alertness_matrix) > 0:
                alertness_percentiles = self._calc_percentiles(alertness_matrix)

        # Estadísticas escalares
        glucose_stats = {
            "peak": self._calc_scalar_stats(
                [r.peak_glucose for r in valid_results if r.peak_glucose > 0]
            ),
            "auc": self._calc_scalar_stats(
                [r.auc_glucose for r in valid_results if r.auc_glucose > 0]
            ),
            "time_to_peak": self._calc_scalar_stats(
                [r.time_to_peak_glucose for r in valid_results if r.time_to_peak_glucose > 0]
            ),
        }

        caffeine_stats = {
            "peak": self._calc_scalar_stats(
                [r.peak_caffeine for r in valid_results if r.peak_caffeine > 0]
            ),
            "auc": self._calc_scalar_stats(
                [r.auc_caffeine for r in valid_results if r.auc_caffeine > 0]
            ),
            "alertness_peak": self._calc_scalar_stats(
                [r.alertness_peak for r in valid_results if r.alertness_peak > 0]
            ),
        }

        # Risk analysis
        risk_analysis = {
            "pct_hyperglycemia": sum(1 for r in valid_results if r.hyperglycemia_flag)
            / n_valid
            * 100,
            "pct_severe_hyperglycemia": sum(1 for r in valid_results if r.severe_hyperglycemia_flag)
            / n_valid
            * 100,
            "pct_hypoglycemia": sum(1 for r in valid_results if r.hypoglycemia_flag)
            / n_valid
            * 100,
            "pct_crash_risk": sum(1 for r in valid_results if r.crash_risk_flag) / n_valid * 100,
            "pct_jitter_risk": sum(1 for r in valid_results if r.jitter_risk_flag) / n_valid * 100,
            "pct_sleep_disruption": sum(1 for r in valid_results if r.sleep_risk_flag)
            / n_valid
            * 100,
        }

        # Subgroup analysis
        subgroup_analysis = {
            "by_bmi": self._analyze_by_bmi(population, individual_results),
            "by_age": self._analyze_by_age(population, individual_results),
            "by_activity": self._analyze_by_activity(population, individual_results),
        }

        # Individual results (respeta config.store_individual_results)
        stored_individual = individual_results if config.store_individual_results else []

        return PopulationResults(
            simulation_id=sim_id,
            product=product.to_dict(),
            config=asdict(config),
            adapter_config=self.glucose_adapter.config.to_dict(),  # NUEVO: trazabilidad
            timestamp=datetime.now().isoformat(),
            duration_seconds=time.time() - start_time,
            n_individuals=n_total,
            n_valid=n_valid,
            population_summary=pop_summary,
            time_points=time_points,
            glucose_percentiles=glucose_percentiles,
            caffeine_percentiles=caffeine_percentiles,
            alertness_percentiles=alertness_percentiles,
            glucose_stats=glucose_stats,
            caffeine_stats=caffeine_stats,
            risk_analysis=risk_analysis,
            subgroup_analysis=subgroup_analysis,
            individual_results=stored_individual,
        )

    def _calc_percentiles(self, matrix: np.ndarray) -> Dict[str, List[float]]:
        """Calcula percentiles a lo largo del eje de personas."""
        if len(matrix) == 0:
            return {}
        return {
            "p05": np.percentile(matrix, 5, axis=0).tolist(),
            "p25": np.percentile(matrix, 25, axis=0).tolist(),
            "p50": np.percentile(matrix, 50, axis=0).tolist(),
            "p75": np.percentile(matrix, 75, axis=0).tolist(),
            "p95": np.percentile(matrix, 95, axis=0).tolist(),
            "mean": np.mean(matrix, axis=0).tolist(),
        }

    def _calc_scalar_stats(self, values: List[float]) -> Dict[str, float]:
        """Calcula estadísticas de una lista de escalares."""
        if not values:
            return {}
        arr = np.array(values)
        return {
            "mean": float(np.mean(arr)),
            "std": float(np.std(arr)),
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
            "p10": float(np.percentile(arr, 10)),
            "p50": float(np.percentile(arr, 50)),
            "p90": float(np.percentile(arr, 90)),
        }

    def _analyze_by_bmi(
        self,
        population: List[VirtualPerson],
        results: List[IndividualResult],
    ) -> Dict[str, Dict[str, float]]:
        """Análisis de riesgo por categoría BMI."""
        from collections import defaultdict

        groups = defaultdict(list)
        for person, res in zip(population, results):
            if res.valid:
                groups[person.bmi_category].append(res)

        analysis = {}
        for cat, group_results in groups.items():
            n = len(group_results)
            if n > 0:
                analysis[cat] = {
                    "n": n,
                    "pct_hyperglycemia": sum(1 for r in group_results if r.hyperglycemia_flag)
                    / n
                    * 100,
                    "pct_crash_risk": sum(1 for r in group_results if r.crash_risk_flag) / n * 100,
                    "avg_peak_glucose": float(
                        np.mean([r.peak_glucose for r in group_results if r.peak_glucose > 0])
                    ),
                }
        return analysis

    def _analyze_by_age(
        self,
        population: List[VirtualPerson],
        results: List[IndividualResult],
    ) -> Dict[str, Dict[str, float]]:
        """Análisis de riesgo por grupo de edad."""
        from collections import defaultdict

        def age_group(age: int) -> str:
            if age < 30:
                return "18-29"
            elif age < 45:
                return "30-44"
            elif age < 60:
                return "45-59"
            else:
                return "60+"

        groups = defaultdict(list)
        for person, res in zip(population, results):
            if res.valid:
                groups[age_group(person.age)].append(res)

        analysis = {}
        for grp, group_results in groups.items():
            n = len(group_results)
            if n > 0:
                analysis[grp] = {
                    "n": n,
                    "pct_hyperglycemia": sum(1 for r in group_results if r.hyperglycemia_flag)
                    / n
                    * 100,
                    "pct_crash_risk": sum(1 for r in group_results if r.crash_risk_flag) / n * 100,
                }
        return analysis

    def _analyze_by_activity(
        self,
        population: List[VirtualPerson],
        results: List[IndividualResult],
    ) -> Dict[str, Dict[str, float]]:
        """Análisis de riesgo por nivel de actividad."""
        from collections import defaultdict

        groups = defaultdict(list)
        for person, res in zip(population, results):
            if res.valid:
                groups[person.activity_level].append(res)

        analysis = {}
        for act, group_results in groups.items():
            n = len(group_results)
            if n > 0:
                analysis[act] = {
                    "n": n,
                    "pct_hyperglycemia": sum(1 for r in group_results if r.hyperglycemia_flag)
                    / n
                    * 100,
                    "avg_alertness": float(
                        np.mean([r.alertness_peak for r in group_results if r.alertness_peak > 0])
                    ),
                }
        return analysis

    def _create_empty_results(
        self,
        product: ProductComposition,
        config: SimulationConfig,
        start_time: float,
        population: List[VirtualPerson],
    ) -> PopulationResults:
        """Crea resultados vacíos cuando no hay simulaciones válidas."""
        return PopulationResults(
            simulation_id="FAILED",
            product=product.to_dict(),
            config=asdict(config),
            timestamp=datetime.now().isoformat(),
            duration_seconds=time.time() - start_time,
            n_individuals=len(population),
            n_valid=0,
            population_summary=self.population_generator.get_population_summary(population),
            time_points=[],
            glucose_percentiles={},
            caffeine_percentiles={},
            alertness_percentiles={},
            glucose_stats={},
            caffeine_stats={},
            risk_analysis={},
            subgroup_analysis={},
            individual_results=[],
        )
