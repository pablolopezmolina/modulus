# src/core/population/distributions.py
# MODULUS — Statistical Distributions & Sampling
#
# Implementa las distribuciones estadísticas basadas en datos NHANES
# y literatura científica para generar parámetros poblacionales realistas.
#
# Key features:
# - Truncated distributions (parámetros fisiológicos tienen límites)
# - Correlated sampling (BMI correlaciona con insulin sensitivity)
# - Latin Hypercube Sampling para cobertura eficiente

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

import numpy as np
from scipy import stats
from scipy.stats import qmc


@dataclass
class DistributionSpec:
    """Especificación de una distribución estadística."""

    dist_type: str
    params: Dict[str, Any]

    def sample(self, rng: np.random.Generator, size: int = 1) -> np.ndarray:
        """Genera muestras de esta distribución."""
        return sample_distribution(self.dist_type, self.params, rng, size)


def sample_distribution(
    dist_type: str, params: Dict[str, Any], rng: np.random.Generator, size: int = 1
) -> np.ndarray:
    """
    Genera muestras de una distribución especificada.

    Args:
        dist_type: Tipo de distribución
        params: Parámetros de la distribución
        rng: Generador de números aleatorios
        size: Número de muestras

    Returns:
        Array de muestras

    Supported distributions:
        - truncated_normal: Normal truncada en [min, max]
        - lognormal: Log-normal con parámetros mean_log, std_log
        - beta_scaled: Beta escalada a rango [min, max]
        - categorical: Categórica con probabilidades
        - bernoulli: Bernoulli con probabilidad p
        - constant: Valor constante
        - mixture: Mezcla de distribuciones
    """
    if dist_type == "truncated_normal":
        return _sample_truncated_normal(params, rng, size)
    elif dist_type == "lognormal":
        return _sample_lognormal(params, rng, size)
    elif dist_type == "beta_scaled":
        return _sample_beta_scaled(params, rng, size)
    elif dist_type == "categorical":
        return _sample_categorical(params, rng, size)
    elif dist_type == "bernoulli":
        return _sample_bernoulli(params, rng, size)
    elif dist_type == "constant":
        return np.full(size, params.get("value", 0))
    elif dist_type == "mixture":
        return _sample_mixture(params, rng, size)
    else:
        raise ValueError(f"Unknown distribution type: {dist_type}")


def _sample_truncated_normal(
    params: Dict[str, Any], rng: np.random.Generator, size: int
) -> np.ndarray:
    """Muestrea de una normal truncada."""
    mean = params["mean"]
    std = params["std"]
    lo = params.get("min", -np.inf)
    hi = params.get("max", np.inf)

    # Estandarizar límites
    a = (lo - mean) / std if std > 0 else 0
    b = (hi - mean) / std if std > 0 else 0

    # scipy.stats.truncnorm usa límites estandarizados
    samples = stats.truncnorm.rvs(a, b, loc=mean, scale=std, size=size, random_state=rng)
    return samples


def _sample_lognormal(params: Dict[str, Any], rng: np.random.Generator, size: int) -> np.ndarray:
    """Muestrea de una log-normal, con truncamiento opcional."""
    mean_log = params["mean_log"]
    std_log = params["std_log"]

    samples = rng.lognormal(mean=mean_log, sigma=std_log, size=size)

    # Truncamiento opcional
    lo = params.get("min")
    hi = params.get("max")
    if lo is not None:
        samples = np.maximum(samples, lo)
    if hi is not None:
        samples = np.minimum(samples, hi)

    return samples


def _sample_beta_scaled(params: Dict[str, Any], rng: np.random.Generator, size: int) -> np.ndarray:
    """
    Muestrea de una Beta escalada al rango [min, max].

    Beta(α, β) genera valores en [0, 1], luego escalamos.
    """
    alpha = params["alpha"]
    beta_param = params["beta"]
    lo = params["min"]
    hi = params["max"]

    samples = rng.beta(alpha, beta_param, size=size)
    return lo + samples * (hi - lo)


def _sample_categorical(params: Dict[str, Any], rng: np.random.Generator, size: int) -> np.ndarray:
    """Muestrea de una distribución categórica."""
    categories = params["categories"]
    probs = params["probabilities"]

    # Normalizar probabilidades por si acaso
    probs = np.array(probs, dtype=float)
    probs = probs / probs.sum()

    indices = rng.choice(len(categories), size=size, p=probs)
    return np.array([categories[i] for i in indices])


def _sample_bernoulli(params: Dict[str, Any], rng: np.random.Generator, size: int) -> np.ndarray:
    """Muestrea de una Bernoulli."""
    p = params.get("probability", params.get("p", 0.5))
    return rng.random(size) < p


def _sample_mixture(params: Dict[str, Any], rng: np.random.Generator, size: int) -> np.ndarray:
    """
    Muestrea de una mezcla de distribuciones.

    params["components"] es una lista de:
    {"weight": float, "distribution": str, ...otros params...}
    """
    components = params["components"]
    weights = np.array([c["weight"] for c in components])
    weights = weights / weights.sum()

    # Asignar cada muestra a un componente
    component_indices = rng.choice(len(components), size=size, p=weights)

    samples = np.zeros(size)
    for i, comp in enumerate(components):
        mask = component_indices == i
        n_comp = mask.sum()
        if n_comp > 0:
            comp_params = {k: v for k, v in comp.items() if k not in ("weight", "distribution")}
            samples[mask] = sample_distribution(comp["distribution"], comp_params, rng, n_comp)

    return samples


class LatinHypercubeSampler:
    """
    Latin Hypercube Sampling para generación eficiente de poblaciones.

    LHS proporciona mejor cobertura del espacio de parámetros que
    muestreo aleatorio puro, especialmente importante para N pequeño.

    Ejemplo:
        Con N=100 muestras de edad [20, 80]:
        - Random: Puede tener 3 muestras en [20, 30] y 15 en [50, 60]
        - LHS: Garantiza ~1.67 muestras por cada intervalo de 10 años
    """

    def __init__(self, n_dimensions: int, seed: Optional[int] = None):
        """
        Args:
            n_dimensions: Número de variables a muestrear
            seed: Semilla para reproducibilidad
        """
        self.n_dims = n_dimensions
        self.seed = seed
        self._sampler = qmc.LatinHypercube(d=n_dimensions, seed=seed)

    def sample(self, n_samples: int) -> np.ndarray:
        """
        Genera n_samples puntos en [0, 1]^d usando LHS.

        Returns:
            Array de shape (n_samples, n_dimensions) con valores en [0, 1]
        """
        return self._sampler.random(n=n_samples)

    @staticmethod
    def transform_to_distribution(
        uniform_samples: np.ndarray, dist_type: str, params: Dict[str, Any]
    ) -> np.ndarray:
        """
        Transforma muestras uniformes [0, 1] a una distribución objetivo.

        Usa la función de cuantiles (inverse CDF) para la transformación.
        """
        if dist_type == "truncated_normal":
            mean = params["mean"]
            std = params["std"]
            lo = params.get("min", -np.inf)
            hi = params.get("max", np.inf)

            a = (lo - mean) / std if std > 0 else 0
            b = (hi - mean) / std if std > 0 else 0

            return stats.truncnorm.ppf(uniform_samples, a, b, loc=mean, scale=std)

        elif dist_type == "lognormal":
            mean_log = params["mean_log"]
            std_log = params["std_log"]
            samples = stats.lognorm.ppf(uniform_samples, s=std_log, scale=np.exp(mean_log))

            # Truncamiento
            lo = params.get("min")
            hi = params.get("max")
            if lo is not None:
                samples = np.maximum(samples, lo)
            if hi is not None:
                samples = np.minimum(samples, hi)
            return samples

        elif dist_type == "beta_scaled":
            alpha = params["alpha"]
            beta_param = params["beta"]
            lo = params["min"]
            hi = params["max"]

            beta_samples = stats.beta.ppf(uniform_samples, alpha, beta_param)
            return lo + beta_samples * (hi - lo)

        elif dist_type == "constant":
            return np.full(len(uniform_samples), params.get("value", 0))

        else:
            raise ValueError(f"LHS transform not implemented for: {dist_type}")


class CorrelationMatrix:
    """
    Maneja correlaciones entre variables para generar parámetros realistas.

    Ejemplo: BMI alto → insulin_sensitivity baja (correlación negativa)

    Usa la transformación de Cholesky para inducir correlaciones en
    muestras independientes.
    """

    def __init__(self, n_vars: int):
        """Inicializa con matriz de correlación identidad."""
        self.n_vars = n_vars
        self.correlation_matrix = np.eye(n_vars)
        self.var_names: List[str] = [f"var_{i}" for i in range(n_vars)]

    def set_variable_names(self, names: List[str]) -> None:
        """Asigna nombres a las variables."""
        if len(names) != self.n_vars:
            raise ValueError(f"Expected {self.n_vars} names, got {len(names)}")
        self.var_names = names

    def set_correlation(self, var1: Union[str, int], var2: Union[str, int], rho: float) -> None:
        """
        Establece correlación entre dos variables.

        Args:
            var1, var2: Nombres o índices de variables
            rho: Coeficiente de correlación [-1, 1]
        """
        if not -1 <= rho <= 1:
            raise ValueError(f"Correlation must be in [-1, 1], got {rho}")

        i = self._get_index(var1)
        j = self._get_index(var2)

        self.correlation_matrix[i, j] = rho
        self.correlation_matrix[j, i] = rho

    def _get_index(self, var: Union[str, int]) -> int:
        if isinstance(var, int):
            return var
        return self.var_names.index(var)

    def is_positive_definite(self) -> bool:
        """Verifica que la matriz de correlación sea válida."""
        try:
            np.linalg.cholesky(self.correlation_matrix)
            return True
        except np.linalg.LinAlgError:
            return False

    def induce_correlation(self, independent_samples: np.ndarray) -> np.ndarray:
        """
        Transforma muestras independientes para tener las correlaciones deseadas.

        Usa la transformación de Iman-Conover (basada en rankings).

        Args:
            independent_samples: Array (n_samples, n_vars) de muestras independientes

        Returns:
            Array con las mismas distribuciones marginales pero correlacionadas
        """
        n_samples, n_vars = independent_samples.shape

        if n_vars != self.n_vars:
            raise ValueError(f"Expected {self.n_vars} variables, got {n_vars}")

        if not self.is_positive_definite():
            # Intentar hacer la matriz semidefinida positiva
            self.correlation_matrix = self._nearest_positive_definite(self.correlation_matrix)

        # Descomposición de Cholesky
        L = np.linalg.cholesky(self.correlation_matrix)

        # Generar muestras normales correlacionadas
        # Usamos el ranking de las muestras originales
        n_samples, n_vars = independent_samples.shape

        # Convertir a rankings normales
        rankings = np.zeros_like(independent_samples)
        for j in range(n_vars):
            order = np.argsort(independent_samples[:, j])
            rankings[order, j] = np.arange(n_samples)

        # Normalizar rankings a cuantiles normales
        normal_scores = stats.norm.ppf((rankings + 0.5) / n_samples)

        # Inducir correlación
        correlated_scores = (L @ normal_scores.T).T

        # Re-rankear para recuperar distribuciones originales
        result = np.zeros_like(independent_samples)
        for j in range(n_vars):
            sorted_original = np.sort(independent_samples[:, j])
            new_order = np.argsort(np.argsort(correlated_scores[:, j]))
            result[:, j] = sorted_original[new_order]

        return result

    @staticmethod
    def _nearest_positive_definite(A: np.ndarray) -> np.ndarray:
        """
        Encuentra la matriz semidefinida positiva más cercana.
        Algoritmo de Higham (2002).
        """
        B = (A + A.T) / 2
        _, s, V = np.linalg.svd(B)
        H = V.T @ np.diag(s) @ V
        A2 = (B + H) / 2
        A3 = (A2 + A2.T) / 2

        if np.all(np.linalg.eigvalsh(A3) > 0):
            return A3

        # Si aún no es PD, añadir pequeña diagonal
        spacing = np.spacing(np.linalg.norm(A))
        I = np.eye(A.shape[0])
        k = 1
        while not np.all(np.linalg.eigvalsh(A3) > 0):
            min_eig = np.min(np.real(np.linalg.eigvalsh(A3)))
            A3 += I * (-min_eig * k**2 + spacing)
            k += 1

        return A3


class PopulationDistributions:
    """
    Carga y gestiona las distribuciones poblacionales desde el JSON de configuración.

    Proporciona una interfaz limpia para acceder a las distribuciones
    de cada parámetro.
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Args:
            config_path: Ruta al archivo population_params.json
                        Si None, usa la ruta por defecto
        """
        if config_path is None:
            # Ruta por defecto relativa al proyecto
            config_path = (
                Path(__file__).parent.parent.parent.parent
                / "data"
                / "reference"
                / "population_params.json"
            )

        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Carga la configuración desde JSON."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Population config not found: {self.config_path}")

        with open(self.config_path, "r") as f:
            self._config = json.load(f)

    def get_distribution(self, *path: str) -> DistributionSpec:
        """
        Obtiene la especificación de distribución para un parámetro.

        Args:
            *path: Ruta jerárquica al parámetro
                   Ej: get_distribution("demographics", "age")
                       get_distribution("caffeine_metabolism", "half_life_hours", "normal")

        Returns:
            DistributionSpec con tipo y parámetros
        """
        node = self._config
        for key in path:
            if key not in node:
                raise KeyError(f"Config path not found: {'.'.join(path)}")
            node = node[key]

        if not isinstance(node, dict) or "distribution" not in node:
            raise ValueError(f"No distribution spec at: {'.'.join(path)}")

        dist_type = node["distribution"]
        params = {k: v for k, v in node.items() if k != "distribution"}

        return DistributionSpec(dist_type=dist_type, params=params)

    def get_sex_specific_distribution(
        self, category: str, param: str, sex: str
    ) -> DistributionSpec:
        """
        Obtiene distribución específica por sexo.

        Ej: get_sex_specific_distribution("demographics", "weight_kg", "male")
        """
        return self.get_distribution(category, param, sex)

    def get_genotype_specific_distribution(self, param: str, genotype: str) -> DistributionSpec:
        """
        Obtiene distribución específica por genotipo CYP1A2.

        Ej: get_genotype_specific_distribution("half_life_hours", "slow")
        """
        return self.get_distribution("caffeine_metabolism", param, genotype)

    def get_correlations(self) -> Dict[str, Dict[str, float]]:
        """Retorna las correlaciones definidas entre parámetros."""
        return self._config.get("glucose_metabolism", {}).get("correlations", {})

    def get_activity_insulin_multipliers(self) -> Dict[str, float]:
        """Retorna los multiplicadores de insulina por nivel de actividad."""
        return (
            self._config.get("lifestyle", {})
            .get("activity_level", {})
            .get("insulin_sensitivity_multiplier", {})
        )

    def get_subpopulation_preset(self, name: str) -> Dict[str, Any]:
        """
        Obtiene los overrides para una subpoblación predefinida.

        Ej: get_subpopulation_preset("athletes")
        """
        presets = self._config.get("subpopulation_presets", {})
        if name not in presets:
            raise KeyError(f"Unknown preset: {name}. Available: {list(presets.keys())}")
        return presets[name]

    @property
    def available_presets(self) -> List[str]:
        """Lista de subpoblaciones predefinidas disponibles."""
        return list(self._config.get("subpopulation_presets", {}).keys())
