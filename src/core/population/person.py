# src/core/population/person.py
# MODULUS — Virtual Person representation
#
# Dataclass inmutable que encapsula todos los parámetros fisiológicos de un individuo virtual.
# Diseñado para ser compatible con GlucoseModel (Dalla Man) y CaffeineModel (1-compartment PK).
#
# V2.0: Integra lógica fisiológica profunda basada en literatura:
# - Escalado alométrico para volúmenes de distribución
# - Ajustes por composición corporal (obesidad reduce Vd relativo)
# - Correlaciones fisiológicas (smoker → CYP1A2 induction)

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, Literal
import hashlib
import json
import numpy as np

# Type aliases para claridad
Sex = Literal["male", "female"]
Genotype = Literal["slow", "normal", "fast"]
ActivityLevel = Literal["sedentary", "light", "moderate", "active", "very_active"]


@dataclass(frozen=True)
class VirtualPerson:
    """
    Representa un individuo virtual con parámetros fisiológicos realistas.
    
    Inmutable (frozen=True) para garantizar reproducibilidad en simulaciones paralelas.
    Cada persona tiene un ID único basado en hash de sus parámetros.
    
    Physiological Parameters:
        Demographics:
            age: Edad en años (18-65)
            sex: Sexo biológico ('male' o 'female')
            weight_kg: Peso en kg
            height_cm: Altura en cm
        
        Metabolismo de glucosa:
            fasting_glucose_mg_dl: Glucosa en ayunas (mg/dL)
            fasting_insulin_mu_l: Insulina en ayunas (mU/L)
            insulin_sensitivity_factor: Factor multiplicador (0.3-1.7), 1.0 = normal
            beta_cell_function: Función de células beta (0.5-1.5), 1.0 = normal
            gastric_emptying_speed: Velocidad vaciado gástrico (0.5-1.5), 1.0 = normal
        
        Metabolismo de cafeína:
            cyp1a2_genotype: Genotipo CYP1A2 ('slow', 'normal', 'fast')
            caffeine_half_life_h: Vida media de cafeína (horas)
            habitual_caffeine_mg: Consumo diario habitual de cafeína (mg)
        
        Estilo de vida:
            activity_level: Nivel de actividad física
            smoker: Si es fumador (afecta CYP1A2 - inducción 1.5x)
    """
    
    # === Demographics ===
    age: int
    sex: Sex
    weight_kg: float
    height_cm: float
    
    # === Glucose Metabolism ===
    fasting_glucose_mg_dl: float
    fasting_insulin_mu_l: float
    insulin_sensitivity_factor: float  # 1.0 = Normal, <1.0 = Resistente
    
    # === Caffeine Metabolism ===
    cyp1a2_genotype: Genotype
    caffeine_half_life_h: float
    habitual_caffeine_mg: float
    
    # === Lifestyle ===
    activity_level: ActivityLevel
    smoker: bool
    
    # === Extended Glucose Metabolism (with defaults) ===
    beta_cell_function: float = 1.0    # 1.0 = Normal, <1.0 = Reducida
    gastric_emptying_speed: float = 1.0  # 1.0 = Normal, <1.0 = Lento
    
    # === Metadata ===
    person_id: str = field(default="", compare=False)
    generation_seed: Optional[int] = field(default=None, compare=False)
    
    def __post_init__(self) -> None:
        """Generar ID único si no se proporciona."""
        if not self.person_id:
            object.__setattr__(self, 'person_id', self._compute_hash())
    
    def _compute_hash(self) -> str:
        """Genera un hash único basado en los parámetros fisiológicos."""
        params = {
            'age': self.age,
            'sex': self.sex,
            'weight_kg': round(self.weight_kg, 2),
            'height_cm': round(self.height_cm, 2),
            'fasting_glucose_mg_dl': round(self.fasting_glucose_mg_dl, 2),
            'fasting_insulin_mu_l': round(self.fasting_insulin_mu_l, 2),
            'insulin_sensitivity_factor': round(self.insulin_sensitivity_factor, 4),
            'beta_cell_function': round(self.beta_cell_function, 4),
            'gastric_emptying_speed': round(self.gastric_emptying_speed, 4),
            'cyp1a2_genotype': self.cyp1a2_genotype,
            'caffeine_half_life_h': round(self.caffeine_half_life_h, 3),
            'habitual_caffeine_mg': round(self.habitual_caffeine_mg, 1),
            'activity_level': self.activity_level,
            'smoker': self.smoker,
        }
        json_str = json.dumps(params, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()[:12]
    
    # =========================================================================
    # Derived Properties
    # =========================================================================
    
    @property
    def bmi(self) -> float:
        """Body Mass Index (kg/m²)."""
        height_m = self.height_cm / 100.0
        return self.weight_kg / (height_m ** 2)
    
    @property
    def bmi_category(self) -> str:
        """Categoría de BMI según OMS."""
        bmi = self.bmi
        if bmi < 18.5:
            return "underweight"
        elif bmi < 25:
            return "normal"
        elif bmi < 30:
            return "overweight"
        else:
            return "obese"
    
    @property
    def body_surface_area_m2(self) -> float:
        """Área de superficie corporal (Du Bois formula)."""
        return 0.007184 * (self.weight_kg ** 0.425) * (self.height_cm ** 0.725)
    
    @property
    def lean_body_mass_kg(self) -> float:
        """
        Masa corporal magra estimada (Boer formula).
        Importante para ajustar volúmenes de distribución.
        """
        if self.sex == "male":
            return 0.407 * self.weight_kg + 0.267 * self.height_cm - 19.2
        else:
            return 0.252 * self.weight_kg + 0.473 * self.height_cm - 48.3
    
    @property
    def fat_fraction(self) -> float:
        """Fracción de masa grasa estimada."""
        lbm = max(self.lean_body_mass_kg, self.weight_kg * 0.3)  # Sanity bound
        return max(0.05, 1.0 - (lbm / self.weight_kg))
    
    @property
    def activity_multiplier(self) -> float:
        """
        Multiplicador de sensibilidad a insulina por actividad física.
        Source: population_params.json
        """
        multipliers = {
            "sedentary": 0.85,
            "light": 0.95,
            "moderate": 1.0,
            "active": 1.15,
            "very_active": 1.30,
        }
        return multipliers.get(self.activity_level, 1.0)
    
    @property
    def effective_insulin_sensitivity(self) -> float:
        """
        Factor de sensibilidad a insulina efectivo.
        Combina factor base + ajuste por actividad física.
        """
        return self.insulin_sensitivity_factor * self.activity_multiplier
    
    @property
    def caffeine_tolerance_factor(self) -> float:
        """
        Factor de reducción de efecto de cafeína por tolerancia.
        Consumidores habituales tienen respuesta reducida (shift EC50).
        
        Returns: 0.6 (40% reducción max) a 1.0 (sin tolerancia)
        """
        reduction_per_100mg = 0.05
        max_reduction = 0.40
        reduction = min(
            (self.habitual_caffeine_mg / 100.0) * reduction_per_100mg,
            max_reduction
        )
        return 1.0 - reduction
    
    @property
    def smoking_cyp1a2_induction(self) -> float:
        """
        Factor de inducción de CYP1A2 por tabaquismo.
        Fumadores metabolizan cafeína ~1.5x más rápido.
        Source: Sachse 1999, population_params.json
        """
        return 1.5 if self.smoker else 1.0
    
    # =========================================================================
    # Model Parameter Adapters - Dalla Man Glucose Model
    # =========================================================================
    
    def get_dalla_man_overrides(self) -> Dict[str, float]:
        """
        Genera parámetros específicos para el modelo Dalla Man (2007).
        
        Realiza:
        - Escalado por peso corporal
        - Ajuste de sensibilidad a insulina (Vmx, kp3, p2U)
        - Ajuste de dinámica gástrica (kmax, kmin, kabs)
        - Corrección de volumen de distribución por composición corporal
        
        Reference values from: Dalla Man et al., IEEE TBME 2007
        Reference subject: 78 kg healthy adult
        """
        # === Factores de escala ===
        Sf = self.effective_insulin_sensitivity  # Sensibilidad a insulina
        Gf = self.gastric_emptying_speed         # Velocidad gástrica
        Bf = self.beta_cell_function             # Función células beta
        
        # === Parámetros base del modelo (Tabla I del paper) ===
        overrides = {
            # Demografía
            "BW": float(self.weight_kg),
            "Gb": float(self.fasting_glucose_mg_dl),
            "Ib": float(self.fasting_insulin_mu_l),
            
            # === Dinámica de Insulina (escalado por sensibilidad) ===
            # Vmx: Consumo muscular dependiente de insulina [mg/kg/min per pmol/L]
            "Vmx": 0.047 * Sf,
            # kp3: Supresión hepática de EGP por insulina [mg/kg/min per pmol/L]  
            "kp3": 0.009 * Sf,
            # p2U: Acción de insulina en utilización periférica [min^-1]
            "p2U": 0.0331 * Sf,
            
            # === Dinámica Gástrica (escalado por velocidad) ===
            # kmax: Máxima tasa de vaciado gástrico [min^-1]
            "kmax": 0.0558 * Gf,
            # kmin: Mínima tasa de vaciado gástrico [min^-1]
            "kmin": 0.0080 * Gf,
            # kabs: Tasa de absorción intestinal [min^-1]
            "kabs": 0.057 * Gf,
            
            # === Secreción de Insulina (escalado por función beta) ===
            # K: Ganancia de secreción [pmol/kg per mg/dL]
            "K": 2.30 * Bf,
            # alpha: Tasa de secreción estática [min^-1]
            "alpha": 0.050 * Bf,
            # beta: Tasa de secreción dinámica [pmol/kg/min per mg/dL]
            "beta": 0.11 * Bf,
        }
        
        # === Ajuste de Volumen de Distribución de Glucosa (Vg) ===
        # El modelo base asume Vg = 1.88 dL/kg
        # En obesidad, el volumen relativo BAJA porque:
        # - Tejido adiposo tiene menos agua que tejido magro
        # - Glucosa se distribuye principalmente en agua corporal
        if self.bmi > 30:
            # Penalización: -0.5% por cada punto de BMI sobre 30
            # Límite inferior: 0.8 (20% reducción máxima)
            adiposity_penalty = 1.0 - (self.bmi - 30) * 0.005
            overrides["Vg"] = 1.88 * max(0.80, adiposity_penalty)
        elif self.bmi < 18.5:
            # Bajo peso: ligero aumento de Vg relativo
            overrides["Vg"] = 1.88 * 1.05
        else:
            overrides["Vg"] = 1.88
        
        return overrides
    
    # =========================================================================
    # Model Parameter Adapters - Caffeine PK Model
    # =========================================================================
    
    def get_caffeine_overrides(self) -> Dict[str, float]:
        """
        Genera parámetros PK para modelo de Cafeína 1-compartimento.
        
        Basado en:
        - Blanchard & Sawers (1983) - PK en jóvenes vs elderly
        - Sachse (1999) - Polimorfismo CYP1A2
        - Handbook of Methylxanthines
        
        Ajustes:
        - Vd_per_kg: Por sexo y composición corporal
        - kel: Por half-life individual + inducción por tabaco
        - ka: Por velocidad de vaciado gástrico
        - ec50_mg_l: Por tolerancia (consumidores habituales)
        """
        # === Volumen de Distribución (Vd) ===
        # Base: 0.6-0.7 L/kg, dependiente de agua corporal
        # Mujeres tienen menor agua corporal relativa
        # Obesidad también reduce Vd relativo (más grasa = menos agua)
        
        vd_base = 0.65  # L/kg
        
        # Ajuste por sexo
        if self.sex == "female":
            vd_base = 0.60
        
        # Ajuste por composición corporal
        if self.bmi > 30:
            # Reducción por mayor fracción grasa
            vd_base *= (1.0 - (self.fat_fraction - 0.25) * 0.3)
            vd_base = max(0.45, vd_base)  # Límite inferior
        
        # === Constante de Eliminación (kel) ===
        # kel = ln(2) / t½
        # t½ ya incluye efecto del genotipo (calculado en generator)
        # Aplicamos factor de inducción por tabaco aquí
        
        half_life_min = self.caffeine_half_life_h * 60.0
        base_kel = np.log(2) / half_life_min
        
        # Tabaco induce CYP1A2 → mayor clearance
        effective_kel = base_kel * self.smoking_cyp1a2_induction
        
        # === Constante de Absorción (ka) ===
        # Base: 0.11 min^-1 (rápida, ~6 min t½ absorción)
        # Modificada por velocidad gástrica
        ka = 0.11 * self.gastric_emptying_speed
        
        # === EC50 para modelo PD de Alertness ===
        # Base: 4.0 mg/L
        # Tolerancia desplaza EC50 a la derecha (necesita más para mismo efecto)
        tolerance = self.caffeine_tolerance_factor
        effective_ec50 = 4.0 / tolerance  # Si tolerancia=0.6 → EC50=6.67 mg/L
        
        return {
            "Vd_per_kg": float(vd_base),
            "kel": float(effective_kel),
            "ka": float(ka),
            "ec50_mg_l": float(effective_ec50),
        }
    
    # =========================================================================
    # Serialization
    # =========================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario, incluyendo propiedades derivadas."""
        base = asdict(self)
        base.update({
            "bmi": round(self.bmi, 2),
            "bmi_category": self.bmi_category,
            "body_surface_area_m2": round(self.body_surface_area_m2, 4),
            "lean_body_mass_kg": round(self.lean_body_mass_kg, 2),
            "fat_fraction": round(self.fat_fraction, 3),
            "effective_insulin_sensitivity": round(self.effective_insulin_sensitivity, 4),
            "caffeine_tolerance_factor": round(self.caffeine_tolerance_factor, 4),
            "smoking_cyp1a2_induction": self.smoking_cyp1a2_induction,
        })
        return base
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VirtualPerson":
        """Crea VirtualPerson desde diccionario (ignora campos derivados)."""
        valid_fields = {
            'age', 'sex', 'weight_kg', 'height_cm',
            'fasting_glucose_mg_dl', 'fasting_insulin_mu_l', 'insulin_sensitivity_factor',
            'beta_cell_function', 'gastric_emptying_speed',
            'cyp1a2_genotype', 'caffeine_half_life_h', 'habitual_caffeine_mg',
            'activity_level', 'smoker', 'person_id', 'generation_seed'
        }
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)
    
    def __repr__(self) -> str:
        return (
            f"VirtualPerson(id={self.person_id}, "
            f"age={self.age}, sex={self.sex}, "
            f"BMI={self.bmi:.1f}, SI={self.effective_insulin_sensitivity:.2f}, "
            f"CYP1A2={self.cyp1a2_genotype}, smoker={self.smoker})"
        )


# =============================================================================
# Factory Helpers
# =============================================================================

def create_reference_person() -> VirtualPerson:
    """
    Crea una persona de referencia basada en los parámetros
    del modelo Dalla Man (2007): 78 kg, 56 años, healthy.
    
    Útil para validación y como baseline.
    """
    return VirtualPerson(
        age=56,
        sex="male",
        weight_kg=78.0,
        height_cm=175.0,
        fasting_glucose_mg_dl=95.0,
        fasting_insulin_mu_l=25.0,
        insulin_sensitivity_factor=1.0,
        beta_cell_function=1.0,
        gastric_emptying_speed=1.0,
        cyp1a2_genotype="normal",
        caffeine_half_life_h=5.0,
        habitual_caffeine_mg=200.0,
        activity_level="moderate",
        smoker=False,
        person_id="reference_dalla_man",
    )


def create_test_person(
    preset: Literal["young_athlete", "elderly_sedentary", "caffeine_sensitive", "insulin_resistant"] = "young_athlete"
) -> VirtualPerson:
    """
    Crea personas de prueba con perfiles predefinidos.
    
    Presets:
    - young_athlete: Joven, activo, alta sensibilidad a insulina
    - elderly_sedentary: Mayor, sedentario, menor sensibilidad
    - caffeine_sensitive: Metabolizador lento de cafeína (CYP1A2 slow)
    - insulin_resistant: Alta resistencia a insulina (pre-diabético, fumador)
    """
    presets = {
        "young_athlete": VirtualPerson(
            age=25,
            sex="male",
            weight_kg=75.0,
            height_cm=180.0,
            fasting_glucose_mg_dl=88.0,
            fasting_insulin_mu_l=12.0,
            insulin_sensitivity_factor=1.4,
            beta_cell_function=1.1,
            gastric_emptying_speed=1.1,
            cyp1a2_genotype="fast",
            caffeine_half_life_h=3.5,
            habitual_caffeine_mg=300.0,
            activity_level="very_active",
            smoker=False,
        ),
        "elderly_sedentary": VirtualPerson(
            age=68,
            sex="female",
            weight_kg=72.0,
            height_cm=160.0,
            fasting_glucose_mg_dl=102.0,
            fasting_insulin_mu_l=18.0,
            insulin_sensitivity_factor=0.7,
            beta_cell_function=0.85,
            gastric_emptying_speed=0.85,
            cyp1a2_genotype="normal",
            caffeine_half_life_h=5.5,
            habitual_caffeine_mg=100.0,
            activity_level="sedentary",
            smoker=False,
        ),
        "caffeine_sensitive": VirtualPerson(
            age=35,
            sex="female",
            weight_kg=60.0,
            height_cm=165.0,
            fasting_glucose_mg_dl=90.0,
            fasting_insulin_mu_l=15.0,
            insulin_sensitivity_factor=1.0,
            beta_cell_function=1.0,
            gastric_emptying_speed=1.0,
            cyp1a2_genotype="slow",
            caffeine_half_life_h=8.5,
            habitual_caffeine_mg=50.0,
            activity_level="light",
            smoker=False,
        ),
        "insulin_resistant": VirtualPerson(
            age=52,
            sex="male",
            weight_kg=105.0,
            height_cm=175.0,
            fasting_glucose_mg_dl=115.0,
            fasting_insulin_mu_l=35.0,
            insulin_sensitivity_factor=0.45,
            beta_cell_function=0.75,
            gastric_emptying_speed=0.9,
            cyp1a2_genotype="normal",
            caffeine_half_life_h=5.0,
            habitual_caffeine_mg=400.0,
            activity_level="sedentary",
            smoker=True,
        ),
    }
    
    if preset not in presets:
        raise ValueError(f"Unknown preset: {preset}. Valid: {list(presets.keys())}")
    
    return presets[preset]
