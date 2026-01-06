# src/core/adapters.py
# MODULUS — Product-to-Model Adapters
#
# Encapsula TODA la lógica de conversión producto → inputs de modelo.
# Centraliza los "hacks" (fibra, grasa, GI) en un único lugar versionado y testeable.
#
# Principio: VirtualPerson tiene fisiología base, Producto tiene composición.
# El Adapter combina ambos SIN doble conteo.

from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple
import numpy as np

from .models import GlucoseInput, CaffeineInput, DallaManParams, CaffeineParams
from .population import VirtualPerson


# =============================================================================
# Adapter Configuration (versionado y testeable)
# =============================================================================


@dataclass
class MealEffectConfig:
    """
    Configuración de efectos de macros sobre absorción.
    Centraliza todos los "números mágicos" para trazabilidad.

    IMPORTANTE: Esta configuración se incluye en el output de cada simulación
    para auditoría y reproducibilidad.

    Fuentes:
    - Fat effect: Dalla Man 2007 + Wolever 1991
    - Fiber effect: Jenkins 1978
    - Protein effect: Nuttall 1984
    - GI effect: Foster-Powell 2002
    """

    # Version for tracking changes
    version: str = "1.0.0"

    # === FAT EFFECTS ===
    # Grasa ralentiza vaciado gástrico (kmax, kmin)
    fat_kmax_reduction_per_10g: float = 0.10  # -10% kmax por cada 10g grasa
    fat_kmax_min_factor: float = 0.50  # Mínimo 50% de kmax original
    fat_kmin_reduction_per_10g: float = 0.08  # -8% kmin por cada 10g grasa
    fat_kmin_min_factor: float = 0.50

    # === FIBER EFFECTS ===
    # Fibra ralentiza absorción intestinal (kabs)
    fiber_kabs_reduction_per_5g: float = 0.08  # -8% kabs por cada 5g fibra
    fiber_kabs_min_factor: float = 0.50

    # === PROTEIN EFFECTS ===
    # Proteína estimula secreción de insulina (incrementa beta)
    # y ralentiza ligeramente vaciado gástrico
    protein_beta_increase_per_20g: float = 0.05  # +5% beta por cada 20g proteína
    protein_beta_max_factor: float = 1.30  # Máximo +30%
    protein_kmax_reduction_per_20g: float = 0.05
    protein_kmax_min_factor: float = 0.70

    # === GLYCEMIC INDEX EFFECTS ===
    # GI modifica la tasa de aparición de glucosa
    # GI=100 (glucosa pura) = baseline
    # GI<70 = absorción más lenta
    gi_reference: float = 100.0
    gi_kabs_scaling: bool = True  # Si True, kabs se escala por GI/100

    def to_dict(self) -> Dict[str, Any]:
        """Serializa para incluir en output de simulación."""
        return {
            "version": self.version,
            "fat_effects": {
                "kmax_reduction_per_10g": self.fat_kmax_reduction_per_10g,
                "kmax_min_factor": self.fat_kmax_min_factor,
                "kmin_reduction_per_10g": self.fat_kmin_reduction_per_10g,
                "kmin_min_factor": self.fat_kmin_min_factor,
            },
            "fiber_effects": {
                "kabs_reduction_per_5g": self.fiber_kabs_reduction_per_5g,
                "kabs_min_factor": self.fiber_kabs_min_factor,
            },
            "protein_effects": {
                "beta_increase_per_20g": self.protein_beta_increase_per_20g,
                "beta_max_factor": self.protein_beta_max_factor,
                "kmax_reduction_per_20g": self.protein_kmax_reduction_per_20g,
                "kmax_min_factor": self.protein_kmax_min_factor,
            },
            "gi_effects": {
                "reference": self.gi_reference,
                "kabs_scaling": self.gi_kabs_scaling,
            },
        }


# Instancia global por defecto
DEFAULT_MEAL_CONFIG = MealEffectConfig()


# =============================================================================
# Glucose Adapter
# =============================================================================


class GlucoseModelAdapter:
    """
    Adapta ProductComposition + VirtualPerson → GlucoseInput + DallaManParams.

    Responsabilidades:
    1. Crear GlucoseInput con carbs del producto
    2. Calcular modificadores de parámetros basados en:
       - Fisiología del individuo (via get_dalla_man_overrides)
       - Composición del producto (fat, fiber, protein, GI)
    3. EVITAR doble conteo: producto NO modifica gastric_emptying_speed
       (eso ya está en persona)
    """

    def __init__(self, config: Optional[MealEffectConfig] = None):
        self.config = config or DEFAULT_MEAL_CONFIG

    def create_input(
        self,
        product: "ProductComposition",
        person: VirtualPerson,
        duration_minutes: float = 240.0,
        time_step_minutes: float = 1.0,
    ) -> GlucoseInput:
        """Crea GlucoseInput desde producto."""
        return GlucoseInput(
            carbs_g=product.carbohydrates_g,
            duration_minutes=duration_minutes,
            time_step_minutes=time_step_minutes,
        )

    def get_param_overrides(
        self,
        product: "ProductComposition",
        person: VirtualPerson,
    ) -> Dict[str, float]:
        """
        Calcula overrides de parámetros combinando persona + producto.

        IMPORTANTE: Separación de responsabilidades
        - Persona: define fisiología base (SI, beta_cell, gastric_speed)
        - Producto: modifica absorción por composición (fat, fiber, GI)

        NO hay doble conteo porque:
        - gastric_emptying_speed de persona escala kmax/kmin BASE
        - fat/fiber del producto aplica modificadores ADICIONALES
        """
        c = self.config
        overrides = {}

        # 1. Obtener overrides fisiológicos de la persona
        person_overrides = person.get_dalla_man_overrides()
        overrides.update(person_overrides)

        # 2. Aplicar efectos del producto SOBRE los valores personalizados
        # (o sobre defaults si no hay override)

        # === FAT EFFECT ===
        if product.fat_g > 0:
            fat_factor = 1.0 - (product.fat_g / 10.0) * c.fat_kmax_reduction_per_10g
            fat_factor = max(c.fat_kmax_min_factor, fat_factor)

            # Aplicar sobre el kmax ya personalizado (o default)
            base_kmax = overrides.get("kmax", 0.0558)
            overrides["kmax"] = base_kmax * fat_factor

            # kmin también se reduce
            kmin_factor = 1.0 - (product.fat_g / 10.0) * c.fat_kmin_reduction_per_10g
            kmin_factor = max(c.fat_kmin_min_factor, kmin_factor)
            base_kmin = overrides.get("kmin", 0.0080)
            overrides["kmin"] = base_kmin * kmin_factor

        # === FIBER EFFECT ===
        if product.fiber_g > 0:
            fiber_factor = 1.0 - (product.fiber_g / 5.0) * c.fiber_kabs_reduction_per_5g
            fiber_factor = max(c.fiber_kabs_min_factor, fiber_factor)

            base_kabs = overrides.get("kabs", 0.057)
            overrides["kabs"] = base_kabs * fiber_factor

        # === PROTEIN EFFECT ===
        if product.protein_g > 0:
            # Proteína aumenta secreción de insulina
            beta_factor = 1.0 + (product.protein_g / 20.0) * c.protein_beta_increase_per_20g
            beta_factor = min(c.protein_beta_max_factor, beta_factor)

            base_beta = overrides.get("beta", 0.11)
            overrides["beta"] = base_beta * beta_factor

            # Proteína también ralentiza ligeramente vaciado
            prot_kmax_factor = 1.0 - (product.protein_g / 20.0) * c.protein_kmax_reduction_per_20g
            prot_kmax_factor = max(c.protein_kmax_min_factor, prot_kmax_factor)
            overrides["kmax"] = overrides.get("kmax", 0.0558) * prot_kmax_factor

        # === GLYCEMIC INDEX EFFECT ===
        if c.gi_kabs_scaling and product.glycemic_index != c.gi_reference:
            # GI < 100 → absorción más lenta
            gi_factor = product.glycemic_index / c.gi_reference
            gi_factor = np.clip(gi_factor, 0.5, 1.5)  # Limitar rango

            base_kabs = overrides.get("kabs", 0.057)
            overrides["kabs"] = base_kabs * gi_factor

        return overrides

    def get_effect_summary(
        self,
        product: "ProductComposition",
        person: VirtualPerson,
    ) -> Dict[str, Any]:
        """
        Devuelve un resumen de los efectos aplicados para trazabilidad.
        """
        c = self.config
        summary = {
            "person_effects": {},
            "product_effects": {},
            "combined_factors": {},
        }

        # Efectos de persona
        person_overrides = person.get_dalla_man_overrides()
        summary["person_effects"] = {
            "insulin_sensitivity": person.effective_insulin_sensitivity,
            "gastric_emptying_speed": person.gastric_emptying_speed,
            "beta_cell_function": person.beta_cell_function,
        }

        # Efectos de producto
        summary["product_effects"] = {
            "fat_g": product.fat_g,
            "fiber_g": product.fiber_g,
            "protein_g": product.protein_g,
            "glycemic_index": product.glycemic_index,
        }

        # Factores combinados
        if product.fat_g > 0:
            summary["combined_factors"]["fat_kmax_factor"] = max(
                c.fat_kmax_min_factor, 1.0 - (product.fat_g / 10.0) * c.fat_kmax_reduction_per_10g
            )

        if product.fiber_g > 0:
            summary["combined_factors"]["fiber_kabs_factor"] = max(
                c.fiber_kabs_min_factor,
                1.0 - (product.fiber_g / 5.0) * c.fiber_kabs_reduction_per_5g,
            )

        if product.glycemic_index != c.gi_reference:
            summary["combined_factors"]["gi_factor"] = np.clip(
                product.glycemic_index / c.gi_reference, 0.5, 1.5
            )

        return summary


# =============================================================================
# Caffeine Adapter
# =============================================================================


class CaffeineModelAdapter:
    """
    Adapta ProductComposition + VirtualPerson → CaffeineInput + CaffeineParams.

    Más simple que glucosa porque la cafeína tiene menos interacciones
    con otros macros.
    """

    def create_input(
        self,
        product: "ProductComposition",
        person: VirtualPerson,
        duration_minutes: float = 240.0,
        time_step_minutes: float = 1.0,
    ) -> CaffeineInput:
        """Crea CaffeineInput desde producto y persona."""
        # Estimar tolerancia basada en consumo habitual
        tolerance_days = (
            int(person.habitual_caffeine_mg / 100) if person.habitual_caffeine_mg > 0 else 0
        )

        return CaffeineInput(
            dose_mg=product.caffeine_mg,
            body_weight_kg=person.weight_kg,
            duration_minutes=duration_minutes,
            time_step_minutes=time_step_minutes,
            tolerance_days=tolerance_days,
        )

    def get_param_overrides(
        self,
        product: "ProductComposition",
        person: VirtualPerson,
    ) -> Dict[str, float]:
        """
        Calcula overrides de parámetros PK de cafeína.

        Principalmente viene de la persona (CYP1A2, peso, tolerancia).
        Producto no afecta mucho a PK (la dosis ya está en el input).
        """
        return person.get_caffeine_overrides()


# =============================================================================
# Factory Function
# =============================================================================


def create_adapters(
    meal_config: Optional[MealEffectConfig] = None,
) -> Tuple[GlucoseModelAdapter, CaffeineModelAdapter]:
    """
    Crea par de adaptadores con configuración compartida.
    """
    glucose_adapter = GlucoseModelAdapter(config=meal_config)
    caffeine_adapter = CaffeineModelAdapter()
    return glucose_adapter, caffeine_adapter
