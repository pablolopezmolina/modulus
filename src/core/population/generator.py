# src/core/population/generator.py
# MODULUS — Population Generator V2.0
#
# Genera poblaciones virtuales realistas usando Latin Hypercube Sampling
# con correlaciones entre parámetros basadas en datos NHANES.
#
# V2.0 Improvements:
# - Sobre-muestreo para garantizar N individuos con filtros de BMI
# - Correlaciones extendidas: height-weight, glucose-insulin
# - Nuevos campos: beta_cell_function, gastric_emptying_speed
# - Presets de subpoblación respetados para TODAS las variables

import hashlib
import json
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

import numpy as np
from scipy import stats

from .person import VirtualPerson
from .distributions import (
    PopulationDistributions,
    LatinHypercubeSampler,
    CorrelationMatrix,
    sample_distribution,
    DistributionSpec,
)


@dataclass
class GenerationConfig:
    """
    Configuración para generación de población.

    Attributes:
        n_individuals: Número de individuos a generar
        seed: Semilla para reproducibilidad
        use_lhs: Usar Latin Hypercube Sampling (mejor cobertura)
        apply_correlations: Aplicar correlaciones entre parámetros
        bmi_insulin_sensitivity_corr: Correlación BMI ↔ SI (típico: -0.45)
        age_insulin_sensitivity_corr: Correlación Age ↔ SI (típico: -0.25)
        height_weight_corr: Correlación Height ↔ Weight (típico: 0.65)
        glucose_insulin_corr: Correlación Glucose ↔ Insulin (típico: 0.40)
        subpopulation: Preset de subpoblación (athletes, prediabetic, etc.)
        age_range: Rango de edad (override)
        bmi_range: Filtro de BMI (usa sobre-muestreo para garantizar N)
        oversample_factor: Factor de sobre-muestreo para filtros
        max_attempts: Intentos máximos para completar N con filtros
    """

    n_individuals: int = 1000
    seed: Optional[int] = None

    # Sampling method
    use_lhs: bool = True

    # Correlations
    apply_correlations: bool = True
    bmi_insulin_sensitivity_corr: float = -0.45
    age_insulin_sensitivity_corr: float = -0.25
    height_weight_corr: float = 0.65
    glucose_insulin_corr: float = 0.40

    # Subpopulation
    subpopulation: Optional[Literal["athletes", "prediabetic", "elderly", "caffeine_naive"]] = None

    # Constraints
    age_range: Optional[Tuple[int, int]] = None
    bmi_range: Optional[Tuple[float, float]] = None

    # Filter behavior (para garantizar N con filtros)
    oversample_factor: float = 2.5
    max_attempts: int = 10

    def get_config_hash(self) -> str:
        """Genera un hash único de la configuración."""
        config_dict = {
            "n": self.n_individuals,
            "seed": self.seed,
            "lhs": self.use_lhs,
            "corr": self.apply_correlations,
            "bmi_si": self.bmi_insulin_sensitivity_corr,
            "age_si": self.age_insulin_sensitivity_corr,
            "h_w": self.height_weight_corr,
            "g_i": self.glucose_insulin_corr,
            "subpop": self.subpopulation,
            "age_range": self.age_range,
            "bmi_range": self.bmi_range,
        }
        json_str = json.dumps(config_dict, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()[:16]


class PopulationGenerator:
    """
    Genera poblaciones virtuales para simulaciones MODULUS.

    Features:
    - Latin Hypercube Sampling para cobertura eficiente del espacio paramétrico
    - Correlaciones realistas entre parámetros (BMI ↔ SI, Height ↔ Weight, etc.)
    - Soporte completo para subpoblaciones (atletas, prediabéticos, etc.)
    - Sobre-muestreo para garantizar N individuos cuando hay filtros
    - Reproducibilidad completa via semilla

    Usage:
        generator = PopulationGenerator()

        # Población general
        population = generator.generate(n=1000, seed=42)

        # Subpoblación de atletas
        athletes = generator.generate(n=500, subpopulation="athletes", seed=42)

        # Filtro de BMI (garantiza N=500 individuos)
        normal_bmi = generator.generate(config=GenerationConfig(
            n_individuals=500,
            seed=42,
            bmi_range=(18.5, 25.0)
        ))
    """

    # Dimensiones para LHS (variables continuas muestreadas conjuntamente)
    LHS_DIMENSIONS = [
        "age",
        "height",
        "weight",
        "fasting_glucose",
        "fasting_insulin",
        "insulin_sensitivity",
        "beta_cell_function",
        "gastric_emptying_speed",
        "caffeine_half_life",
        "habitual_caffeine",
    ]

    def __init__(self, config_path: Optional[Path] = None):
        """
        Args:
            config_path: Ruta al population_params.json.
                        Si None, usa la ruta por defecto.
        """
        self.distributions = PopulationDistributions(config_path)

    # =========================================================================
    # Public API
    # =========================================================================

    def generate(
        self,
        n: int = 1000,
        seed: Optional[int] = None,
        config: Optional[GenerationConfig] = None,
        subpopulation: Optional[str] = None,
    ) -> List[VirtualPerson]:
        """
        Genera una población virtual.

        Args:
            n: Número de individuos
            seed: Semilla para reproducibilidad
            config: Configuración detallada (anula otros argumentos)
            subpopulation: Preset de subpoblación

        Returns:
            Lista de VirtualPerson (garantiza exactamente N si hay filtros)
        """
        # Construir configuración
        if config is None:
            config = GenerationConfig(
                n_individuals=n,
                seed=seed,
                subpopulation=subpopulation,
            )

        # Si hay filtro de BMI, usar lógica de sobre-muestreo
        if config.bmi_range is not None:
            return self._generate_with_bmi_filter(config)

        # Sin filtros: generación directa
        return self._generate_batch(config, config.n_individuals)

    def get_population_summary(self, population: List[VirtualPerson]) -> Dict[str, Any]:
        """
        Genera estadísticas resumidas de una población.
        Útil para validación y reporting.
        """
        n = len(population)
        if n == 0:
            return {"n": 0, "error": "Empty population"}

        # Extraer arrays
        ages = np.array([p.age for p in population])
        weights = np.array([p.weight_kg for p in population])
        heights = np.array([p.height_cm for p in population])
        bmis = np.array([p.bmi for p in population])
        glucose = np.array([p.fasting_glucose_mg_dl for p in population])
        insulin = np.array([p.fasting_insulin_mu_l for p in population])
        insulin_si = np.array([p.insulin_sensitivity_factor for p in population])
        beta_cell = np.array([p.beta_cell_function for p in population])
        gastric = np.array([p.gastric_emptying_speed for p in population])
        caffeine_hl = np.array([p.caffeine_half_life_h for p in population])

        # Categóricas
        sexes = [p.sex for p in population]
        genotypes = [p.cyp1a2_genotype for p in population]
        activities = [p.activity_level for p in population]

        def describe(arr: np.ndarray) -> Dict[str, float]:
            return {
                "mean": float(np.mean(arr)),
                "std": float(np.std(arr)),
                "min": float(np.min(arr)),
                "max": float(np.max(arr)),
                "p25": float(np.percentile(arr, 25)),
                "p50": float(np.percentile(arr, 50)),
                "p75": float(np.percentile(arr, 75)),
            }

        def count_categories(items: List[str]) -> Dict[str, int]:
            from collections import Counter

            return dict(Counter(items))

        return {
            "n": n,
            "demographics": {
                "age": describe(ages),
                "weight_kg": describe(weights),
                "height_cm": describe(heights),
                "bmi": describe(bmis),
                "sex": count_categories(sexes),
            },
            "glucose_metabolism": {
                "fasting_glucose_mg_dl": describe(glucose),
                "fasting_insulin_mu_l": describe(insulin),
                "insulin_sensitivity_factor": describe(insulin_si),
                "beta_cell_function": describe(beta_cell),
                "gastric_emptying_speed": describe(gastric),
            },
            "caffeine_metabolism": {
                "half_life_h": describe(caffeine_hl),
                "cyp1a2_genotype": count_categories(genotypes),
            },
            "lifestyle": {
                "activity_level": count_categories(activities),
                "smoker_count": sum(1 for p in population if p.smoker),
                "smoker_pct": sum(1 for p in population if p.smoker) / n * 100,
            },
            "correlations": {
                "bmi_insulin_sensitivity": float(np.corrcoef(bmis, insulin_si)[0, 1]),
                "age_insulin_sensitivity": float(np.corrcoef(ages, insulin_si)[0, 1]),
                "height_weight": float(np.corrcoef(heights, weights)[0, 1]),
                "glucose_insulin": float(np.corrcoef(glucose, insulin)[0, 1]),
            },
        }

    # =========================================================================
    # Generation with BMI Filter (Oversampling)
    # =========================================================================

    def _generate_with_bmi_filter(self, config: GenerationConfig) -> List[VirtualPerson]:
        """
        Genera población con filtro de BMI usando sobre-muestreo.
        Garantiza exactamente N individuos (o el máximo posible).
        """
        target_n = config.n_individuals
        collected: List[VirtualPerson] = []

        rng = np.random.default_rng(config.seed)
        attempt = 0

        while len(collected) < target_n and attempt < config.max_attempts:
            # Calcular cuántos faltan y sobre-muestrear
            remaining = target_n - len(collected)
            batch_size = int(remaining * config.oversample_factor)
            batch_size = max(batch_size, remaining + 50)  # Mínimo extra

            # Crear config temporal con nueva semilla
            temp_seed = config.seed if attempt == 0 else int(rng.integers(0, 2**31))
            temp_config = GenerationConfig(
                n_individuals=batch_size,
                seed=temp_seed,
                use_lhs=config.use_lhs,
                apply_correlations=config.apply_correlations,
                bmi_insulin_sensitivity_corr=config.bmi_insulin_sensitivity_corr,
                age_insulin_sensitivity_corr=config.age_insulin_sensitivity_corr,
                height_weight_corr=config.height_weight_corr,
                glucose_insulin_corr=config.glucose_insulin_corr,
                subpopulation=config.subpopulation,
                age_range=config.age_range,
                bmi_range=None,  # No filtrar en batch interno
            )

            batch = self._generate_batch(temp_config, batch_size)

            # Filtrar por BMI
            lo, hi = config.bmi_range
            filtered = [p for p in batch if lo <= p.bmi <= hi]

            # Añadir hasta completar target
            for p in filtered:
                if len(collected) >= target_n:
                    break
                collected.append(p)

            attempt += 1

        if len(collected) < target_n:
            warnings.warn(
                f"Could not generate {target_n} individuals with BMI in {config.bmi_range} "
                f"after {config.max_attempts} attempts. Got {len(collected)}."
            )

        return collected

    # =========================================================================
    # Core Generation Logic
    # =========================================================================

    def _generate_batch(self, config: GenerationConfig, n: int) -> List[VirtualPerson]:
        """Genera un batch de N individuos."""
        rng = np.random.default_rng(config.seed)
        params = self._generate_parameters(config, rng, n)
        return self._create_population(params, config, rng)

    def _generate_parameters(
        self,
        config: GenerationConfig,
        rng: np.random.Generator,
        n: int,
    ) -> Dict[str, np.ndarray]:
        """Genera todos los parámetros para la población."""

        # === Variables categóricas ===
        sex = self._sample_sex(n, config, rng)
        cyp1a2 = self._sample_cyp1a2_genotype(n, config, rng)
        activity = self._sample_activity_level(n, config, rng)
        smoker = self._sample_smoker(n, config, rng)

        # === Variables continuas ===
        if config.use_lhs:
            continuous = self._generate_continuous_lhs(n, config, rng, sex, cyp1a2)
        else:
            continuous = self._generate_continuous_random(n, config, rng, sex, cyp1a2)

        # === Combinar todo ===
        params = {
            "sex": sex,
            "cyp1a2_genotype": cyp1a2,
            "activity_level": activity,
            "smoker": smoker,
            **continuous,
        }

        return params

    # =========================================================================
    # Categorical Sampling
    # =========================================================================

    def _sample_sex(self, n: int, config: GenerationConfig, rng: np.random.Generator) -> np.ndarray:
        """Muestrea sexo biológico."""
        dist_spec = self.distributions.get_distribution("demographics", "sex")
        return sample_distribution(dist_spec.dist_type, dist_spec.params, rng, n)

    def _sample_cyp1a2_genotype(
        self, n: int, config: GenerationConfig, rng: np.random.Generator
    ) -> np.ndarray:
        """Muestrea genotipo CYP1A2."""
        dist_spec = self.distributions.get_distribution("caffeine_metabolism", "cyp1a2_genotype")
        return sample_distribution(dist_spec.dist_type, dist_spec.params, rng, n)

    def _sample_activity_level(
        self, n: int, config: GenerationConfig, rng: np.random.Generator
    ) -> np.ndarray:
        """
        Muestrea nivel de actividad física.
        Respeta overrides de subpopulation (ej: athletes → active/very_active).
        """
        if config.subpopulation:
            try:
                preset = self.distributions.get_subpopulation_preset(config.subpopulation)
                if "activity_level" in preset.get("overrides", {}):
                    override = preset["overrides"]["activity_level"]
                    return sample_distribution(override["distribution"], override, rng, n)
            except KeyError:
                pass

        dist_spec = self.distributions.get_distribution("lifestyle", "activity_level")
        return sample_distribution(dist_spec.dist_type, dist_spec.params, rng, n)

    def _sample_smoker(
        self, n: int, config: GenerationConfig, rng: np.random.Generator
    ) -> np.ndarray:
        """Muestrea estado de fumador."""
        dist_spec = self.distributions.get_distribution("lifestyle", "smoker")
        return sample_distribution(dist_spec.dist_type, dist_spec.params, rng, n)

    # =========================================================================
    # Continuous Sampling - LHS
    # =========================================================================

    def _generate_continuous_lhs(
        self,
        n: int,
        config: GenerationConfig,
        rng: np.random.Generator,
        sex: np.ndarray,
        cyp1a2: np.ndarray,
    ) -> Dict[str, np.ndarray]:
        """Genera variables continuas usando Latin Hypercube Sampling."""
        n_dims = len(self.LHS_DIMENSIONS)

        # Generar muestras uniformes LHS
        lhs_sampler = LatinHypercubeSampler(n_dims, seed=int(rng.integers(0, 2**31)))
        uniform_samples = lhs_sampler.sample(n)

        results = {}

        # Dim 0: Age
        age_dist = self._get_distribution_with_override(config, "demographics", "age")
        results["age"] = LatinHypercubeSampler.transform_to_distribution(
            uniform_samples[:, 0], age_dist.dist_type, age_dist.params
        ).astype(int)

        # Dim 1: Height (sex-specific)
        heights = np.zeros(n)
        for s in ["male", "female"]:
            mask = sex == s
            if mask.any():
                dist = self.distributions.get_sex_specific_distribution(
                    "demographics", "height_cm", s
                )
                heights[mask] = LatinHypercubeSampler.transform_to_distribution(
                    uniform_samples[mask, 1], dist.dist_type, dist.params
                )
        results["height_cm"] = heights

        # Dim 2: Weight (sex-specific)
        weights = np.zeros(n)
        for s in ["male", "female"]:
            mask = sex == s
            if mask.any():
                dist = self.distributions.get_sex_specific_distribution(
                    "demographics", "weight_kg", s
                )
                weights[mask] = LatinHypercubeSampler.transform_to_distribution(
                    uniform_samples[mask, 2], dist.dist_type, dist.params
                )
        results["weight_kg"] = weights

        # Dim 3: Fasting glucose
        glucose_dist = self._get_distribution_with_override(
            config, "glucose_metabolism", "fasting_glucose_mg_dl"
        )
        results["fasting_glucose_mg_dl"] = LatinHypercubeSampler.transform_to_distribution(
            uniform_samples[:, 3], glucose_dist.dist_type, glucose_dist.params
        )

        # Dim 4: Fasting insulin
        insulin_dist = self.distributions.get_distribution(
            "glucose_metabolism", "fasting_insulin_mu_l"
        )
        results["fasting_insulin_mu_l"] = LatinHypercubeSampler.transform_to_distribution(
            uniform_samples[:, 4], insulin_dist.dist_type, insulin_dist.params
        )

        # Dim 5: Insulin sensitivity
        si_dist = self._get_distribution_with_override(
            config, "glucose_metabolism", "insulin_sensitivity_factor"
        )
        results["insulin_sensitivity_factor"] = LatinHypercubeSampler.transform_to_distribution(
            uniform_samples[:, 5], si_dist.dist_type, si_dist.params
        )

        # Dim 6: Beta cell function
        results["beta_cell_function"] = self._sample_beta_cell_function(
            uniform_samples[:, 6], config
        )

        # Dim 7: Gastric emptying speed
        results["gastric_emptying_speed"] = self._sample_gastric_emptying_speed(
            uniform_samples[:, 7], config
        )

        # Dim 8: Caffeine half-life (genotype-specific)
        half_lives = np.zeros(n)
        for geno in ["slow", "normal", "fast"]:
            mask = cyp1a2 == geno
            if mask.any():
                dist = self.distributions.get_genotype_specific_distribution(
                    "half_life_hours", geno
                )
                half_lives[mask] = LatinHypercubeSampler.transform_to_distribution(
                    uniform_samples[mask, 8], dist.dist_type, dist.params
                )
        results["caffeine_half_life_h"] = half_lives

        # Dim 9: Habitual caffeine (mixture - use random sampling)
        caffeine_dist = self._get_habitual_caffeine_distribution(config)
        results["habitual_caffeine_mg"] = sample_distribution(
            caffeine_dist.dist_type, caffeine_dist.params, rng, n
        )

        # Apply correlations
        if config.apply_correlations:
            results = self._apply_correlations(results, config, rng)

        return results

    # =========================================================================
    # Continuous Sampling - Random
    # =========================================================================

    def _generate_continuous_random(
        self,
        n: int,
        config: GenerationConfig,
        rng: np.random.Generator,
        sex: np.ndarray,
        cyp1a2: np.ndarray,
    ) -> Dict[str, np.ndarray]:
        """Genera variables continuas usando muestreo aleatorio simple."""
        results = {}

        # Age
        age_dist = self._get_distribution_with_override(config, "demographics", "age")
        results["age"] = sample_distribution(age_dist.dist_type, age_dist.params, rng, n).astype(
            int
        )

        # Height (sex-specific)
        heights = np.zeros(n)
        for s in ["male", "female"]:
            mask = sex == s
            if mask.any():
                dist = self.distributions.get_sex_specific_distribution(
                    "demographics", "height_cm", s
                )
                heights[mask] = sample_distribution(dist.dist_type, dist.params, rng, mask.sum())
        results["height_cm"] = heights

        # Weight (sex-specific)
        weights = np.zeros(n)
        for s in ["male", "female"]:
            mask = sex == s
            if mask.any():
                dist = self.distributions.get_sex_specific_distribution(
                    "demographics", "weight_kg", s
                )
                weights[mask] = sample_distribution(dist.dist_type, dist.params, rng, mask.sum())
        results["weight_kg"] = weights

        # Fasting glucose
        glucose_dist = self._get_distribution_with_override(
            config, "glucose_metabolism", "fasting_glucose_mg_dl"
        )
        results["fasting_glucose_mg_dl"] = sample_distribution(
            glucose_dist.dist_type, glucose_dist.params, rng, n
        )

        # Fasting insulin
        insulin_dist = self.distributions.get_distribution(
            "glucose_metabolism", "fasting_insulin_mu_l"
        )
        results["fasting_insulin_mu_l"] = sample_distribution(
            insulin_dist.dist_type, insulin_dist.params, rng, n
        )

        # Insulin sensitivity
        si_dist = self._get_distribution_with_override(
            config, "glucose_metabolism", "insulin_sensitivity_factor"
        )
        results["insulin_sensitivity_factor"] = sample_distribution(
            si_dist.dist_type, si_dist.params, rng, n
        )

        # Beta cell function
        results["beta_cell_function"] = self._sample_beta_cell_function(rng.random(n), config)

        # Gastric emptying speed
        results["gastric_emptying_speed"] = self._sample_gastric_emptying_speed(
            rng.random(n), config
        )

        # Caffeine half-life (genotype-specific)
        half_lives = np.zeros(n)
        for geno in ["slow", "normal", "fast"]:
            mask = cyp1a2 == geno
            if mask.any():
                dist = self.distributions.get_genotype_specific_distribution(
                    "half_life_hours", geno
                )
                half_lives[mask] = sample_distribution(dist.dist_type, dist.params, rng, mask.sum())
        results["caffeine_half_life_h"] = half_lives

        # Habitual caffeine
        caffeine_dist = self._get_habitual_caffeine_distribution(config)
        results["habitual_caffeine_mg"] = sample_distribution(
            caffeine_dist.dist_type, caffeine_dist.params, rng, n
        )

        # Apply correlations
        if config.apply_correlations:
            results = self._apply_correlations(results, config, rng)

        return results

    # =========================================================================
    # Special Parameter Samplers
    # =========================================================================

    def _sample_beta_cell_function(
        self, uniform: np.ndarray, config: GenerationConfig
    ) -> np.ndarray:
        """
        Muestrea función de células beta.
        Prediabéticos tienen función reducida.
        """
        if config.subpopulation == "prediabetic":
            # Beta(2, 4) sesgada hacia valores bajos, escalada a [0.5, 1.0]
            return stats.beta.ppf(uniform, 2, 4) * 0.5 + 0.5
        else:
            # Población general: Beta(5, 5) simétrica en [0.8, 1.2]
            return stats.beta.ppf(uniform, 5, 5) * 0.4 + 0.8

    def _sample_gastric_emptying_speed(
        self, uniform: np.ndarray, config: GenerationConfig
    ) -> np.ndarray:
        """
        Muestrea velocidad de vaciado gástrico.
        Elderly tiende a ser más lento.
        """
        if config.subpopulation == "elderly":
            # Sesgado hacia lento [0.7, 1.1]
            return stats.beta.ppf(uniform, 3, 5) * 0.4 + 0.7
        else:
            # Normal [0.8, 1.2]
            return stats.beta.ppf(uniform, 5, 5) * 0.4 + 0.8

    # =========================================================================
    # Distribution Helpers
    # =========================================================================

    def _get_distribution_with_override(
        self, config: GenerationConfig, category: str, param: str
    ) -> DistributionSpec:
        """
        Obtiene distribución, aplicando override de subpoblación si existe.
        """
        if config.subpopulation:
            try:
                preset = self.distributions.get_subpopulation_preset(config.subpopulation)
                if param in preset.get("overrides", {}):
                    override = preset["overrides"][param]
                    return DistributionSpec(override["distribution"], override)
            except KeyError:
                pass

        dist = self.distributions.get_distribution(category, param)

        # Override de rango de edad
        if param == "age" and config.age_range:
            dist.params["min"], dist.params["max"] = config.age_range

        return dist

    def _get_habitual_caffeine_distribution(self, config: GenerationConfig) -> DistributionSpec:
        """Obtiene distribución de consumo de cafeína."""
        if config.subpopulation == "caffeine_naive":
            return DistributionSpec("constant", {"value": 0})

        return self.distributions.get_distribution(
            "caffeine_metabolism", "habitual_caffeine_mg_day"
        )

    # =========================================================================
    # Correlation Application
    # =========================================================================

    def _apply_correlations(
        self, params: Dict[str, np.ndarray], config: GenerationConfig, rng: np.random.Generator
    ) -> Dict[str, np.ndarray]:
        """
        Aplica correlaciones entre variables.

        Correlaciones:
        1. Height ↔ Weight (positiva, ~0.65)
        2. Glucose ↔ Insulin (positiva, ~0.40)
        3. BMI ↔ Insulin Sensitivity (negativa, ~-0.45)
        4. Age ↔ Insulin Sensitivity (negativa, ~-0.25)
        """
        n = len(params["age"])

        # === 1. Correlación Height-Weight ===
        if abs(config.height_weight_corr) > 0.01:
            params = self._apply_rank_correlation(
                params, "height_cm", "weight_kg", config.height_weight_corr, rng
            )

        # === 2. Correlación Glucose-Insulin ===
        if abs(config.glucose_insulin_corr) > 0.01:
            params = self._apply_rank_correlation(
                params,
                "fasting_glucose_mg_dl",
                "fasting_insulin_mu_l",
                config.glucose_insulin_corr,
                rng,
            )

        # === 3 & 4. Correlaciones BMI-SI y Age-SI ===
        # Calcular BMI
        bmi = params["weight_kg"] / (params["height_cm"] / 100) ** 2

        # Z-scores
        bmi_z = self._to_zscore(bmi)
        age_z = self._to_zscore(params["age"])
        si_z = self._to_zscore(params["insulin_sensitivity_factor"])

        si_mean = np.mean(params["insulin_sensitivity_factor"])
        si_std = max(np.std(params["insulin_sensitivity_factor"]), 1e-6)

        rho_bmi = config.bmi_insulin_sensitivity_corr
        rho_age = config.age_insulin_sensitivity_corr

        # Verificar que las correlaciones no excedan 1
        combined_rho_sq = rho_bmi**2 + rho_age**2
        if combined_rho_sq >= 0.95:
            scale = 0.9 / np.sqrt(combined_rho_sq)
            rho_bmi *= scale
            rho_age *= scale
            combined_rho_sq = rho_bmi**2 + rho_age**2

        independent_weight = np.sqrt(max(0, 1 - combined_rho_sq))

        # Nuevo SI en z-scores
        si_z_new = rho_bmi * bmi_z + rho_age * age_z + independent_weight * si_z

        # Des-normalizar y truncar
        si_new = si_z_new * si_std + si_mean
        si_dist = self._get_distribution_with_override(
            config, "glucose_metabolism", "insulin_sensitivity_factor"
        )
        si_min = si_dist.params.get("min", 0.3)
        si_max = si_dist.params.get("max", 1.7)
        params["insulin_sensitivity_factor"] = np.clip(si_new, si_min, si_max)

        return params

    def _apply_rank_correlation(
        self,
        params: Dict[str, np.ndarray],
        var1: str,
        var2: str,
        target_corr: float,
        rng: np.random.Generator,
    ) -> Dict[str, np.ndarray]:
        """
        Aplica correlación usando re-ranking parcial.
        Preserva distribuciones marginales.
        """
        x = params[var1]
        y = params[var2]
        n = len(x)

        # Ordenar y por x para inducir correlación máxima
        x_order = np.argsort(x)
        y_sorted = np.sort(y)

        if target_corr > 0:
            # Correlación positiva: mantener orden
            y_ordered_by_x = y_sorted
        else:
            # Correlación negativa: invertir orden
            y_ordered_by_x = y_sorted[::-1]

        # Mezclar parcialmente para ajustar correlación
        # Proporción a mantener ordenada = |target_corr|
        n_ordered = int(n * abs(target_corr))
        n_shuffled = n - n_ordered

        # Seleccionar índices para shuffle
        all_indices = np.arange(n)
        shuffle_indices = rng.choice(all_indices, size=n_shuffled, replace=False)

        # Crear resultado
        y_new = y_ordered_by_x.copy()
        y_new[shuffle_indices] = rng.permutation(y_new[shuffle_indices])

        # Revertir a posiciones originales
        y_final = np.zeros(n)
        y_final[x_order] = y_new

        params[var2] = y_final
        return params

    def _to_zscore(self, arr: np.ndarray) -> np.ndarray:
        """Convierte array a z-scores."""
        std = max(np.std(arr), 1e-6)
        return (arr - np.mean(arr)) / std

    # =========================================================================
    # Population Creation
    # =========================================================================

    def _create_population(
        self, params: Dict[str, np.ndarray], config: GenerationConfig, rng: np.random.Generator
    ) -> List[VirtualPerson]:
        """Crea VirtualPerson instances desde los parámetros generados."""
        n = len(params["age"])
        population = []

        for i in range(n):
            person = VirtualPerson(
                age=int(params["age"][i]),
                sex=str(params["sex"][i]),
                weight_kg=float(params["weight_kg"][i]),
                height_cm=float(params["height_cm"][i]),
                fasting_glucose_mg_dl=float(params["fasting_glucose_mg_dl"][i]),
                fasting_insulin_mu_l=float(params["fasting_insulin_mu_l"][i]),
                insulin_sensitivity_factor=float(params["insulin_sensitivity_factor"][i]),
                cyp1a2_genotype=str(params["cyp1a2_genotype"][i]),
                caffeine_half_life_h=float(params["caffeine_half_life_h"][i]),
                habitual_caffeine_mg=float(params["habitual_caffeine_mg"][i]),
                activity_level=str(params["activity_level"][i]),
                smoker=bool(params["smoker"][i]),
                beta_cell_function=float(params["beta_cell_function"][i]),
                gastric_emptying_speed=float(params["gastric_emptying_speed"][i]),
                generation_seed=config.seed,
            )
            population.append(person)

        return population
