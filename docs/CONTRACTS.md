# MODULUS — Interface Contracts
# Version: 2.0
# Last Updated: 2025-01-04
#
# ⚠️  ESTE DOCUMENTO DEFINE LAS INTERFACES ENTRE MÓDULOS
# ⚠️  CAMBIAR UN CONTRATO REQUIERE:
#     1. Actualizar este documento
#     2. Actualizar todos los módulos que lo usan
#     3. Actualizar tests de contrato
#     4. Revisión explícita

## 1. CAPA 1 → CAPA 2: Models → Timeline

### Contract 1.1: PhysiologicalModel.simulate()

```python
# ENTRADA
class SimulationInput:
    duration_minutes: float
    time_step_minutes: float
    # ... parámetros específicos del modelo

# SALIDA (INMUTABLE)
class SimulationResult:
    time_points: np.ndarray          # Shape: (N,)
    channels: Dict[str, np.ndarray]  # Cada channel shape: (N,)
    metrics: Dict[str, float]        # Métricas escalares
    metadata: Dict[str, Any]         # Info adicional

# CONTRATO
- time_points DEBE ser monotónicamente creciente
- time_points[0] DEBE ser 0.0
- Todos los channels DEBEN tener len(channel) == len(time_points)
- metrics DEBE incluir al menos: {"is_valid": bool}
- Si is_valid=False, channels pueden estar vacíos
```

### Contract 1.2: VirtualPerson

```python
@dataclass(frozen=True)  # INMUTABLE
class VirtualPerson:
    # Identificación
    person_id: str
    
    # Demographics (REQUERIDOS)
    age: int                    # 18-100
    sex: str                    # "male" | "female"
    weight_kg: float            # 30-300
    height_cm: float            # 100-250
    
    # Metabolismo glucosa (REQUERIDOS)
    fasting_glucose_mg_dl: float
    fasting_insulin_mu_l: float
    insulin_sensitivity_factor: float  # 0.1-3.0, 1.0=normal
    
    # Metabolismo cafeína (REQUERIDOS)
    cyp1a2_genotype: str        # "slow" | "normal" | "fast"
    caffeine_half_life_h: float
    habitual_caffeine_mg: float
    
    # Lifestyle (REQUERIDOS)
    activity_level: str         # "sedentary"|"light"|"moderate"|"active"|"very_active"
    smoker: bool
    
    # Métodos (INMUTABLES)
    def get_glucose_overrides(self) -> Dict[str, float]
    def get_caffeine_overrides(self) -> Dict[str, float]
    
    # Propiedades calculadas
    @property
    def bmi(self) -> float
    @property
    def bmi_category(self) -> str
```

---

## 2. CAPA 2: Timeline Engine

### Contract 2.1: Event

```python
@dataclass(frozen=True)
class Event:
    timestamp_minutes: float     # Minutos desde inicio del día (0-1440)
    event_type: str              # "ingestion" | "meal" | "exercise" | "sleep"
    payload: Dict[str, Any]      # Datos específicos del evento
    
    # Para event_type="ingestion":
    # payload = {
    #     "compound_id": str,
    #     "amount": float,
    #     "unit": str,  # "mg" | "g" | "ml"
    #     "form": str,  # "powder" | "capsule" | "liquid" | "food"
    # }
    
    # Para event_type="meal":
    # payload = {
    #     "carbs_g": float,
    #     "protein_g": float,
    #     "fat_g": float,
    #     "fiber_g": float,
    #     "glycemic_index": float,
    # }

# CONTRATO
- timestamp_minutes DEBE estar en [0, 1440]
- event_type DEBE ser uno de los tipos definidos
- payload DEBE contener los campos requeridos para su tipo
```

### Contract 2.2: Timeline

```python
class Timeline:
    events: List[Event]  # SIEMPRE ordenados por timestamp_minutes
    
    def add_event(self, event: Event) -> "Timeline"  # Retorna NUEVA timeline
    def get_events_in_range(self, start: float, end: float) -> List[Event]
    def validate(self) -> bool  # Verifica consistencia
    
# CONTRATO
- events SIEMPRE está ordenado por timestamp_minutes
- add_event() retorna una NUEVA Timeline (inmutabilidad)
- Dos eventos NO pueden tener exactamente el mismo timestamp
```

### Contract 2.3: PhysiologicalState

```python
@dataclass(frozen=True)
class PhysiologicalState:
    timestamp_minutes: float
    
    # Sistema Glucosa
    glucose_plasma_mg_dl: float
    insulin_plasma_mu_l: float
    glucose_gut_mg: float  # Glucosa pendiente de absorber
    
    # Sistema Cafeína
    caffeine_plasma_mg_l: float
    adenosine_receptor_occupancy: float  # 0-1
    alertness_score: float  # 0-100
    
    # Sistema Aminoácidos (futuro)
    # bcaa_plasma_umol_l: float
    # essential_aa_plasma_umol_l: float
    
    # Sistema Cortisol (futuro)
    # cortisol_plasma_ug_dl: float
    
    # Sistema Energía (futuro)
    # perceived_energy_score: float  # 0-100
    
    # Metadata
    is_fasted: bool
    hours_since_last_meal: float
    
# CONTRATO
- TODOS los valores numéricos DEBEN ser finitos (no NaN, no Inf)
- TODOS los valores DEBEN estar en rangos fisiológicos
- timestamp_minutes DEBE ser >= 0
```

### Contract 2.4: StateIntegrator

```python
class StateIntegrator:
    def __init__(self, person: VirtualPerson, models: Dict[str, PhysiologicalModel])
    
    def step(
        self, 
        current_state: PhysiologicalState, 
        events: List[Event],  # Eventos que ocurren en este step
        dt_minutes: float
    ) -> PhysiologicalState  # Retorna NUEVO estado
    
    def simulate_timeline(
        self,
        initial_state: PhysiologicalState,
        timeline: Timeline,
        dt_minutes: float = 1.0
    ) -> List[PhysiologicalState]  # Un estado por cada timestep

# CONTRATO
- step() SIEMPRE retorna un estado válido
- Si hay error, retorna el estado anterior sin modificar + log warning
- simulate_timeline() retorna estados para t=0, dt, 2*dt, ..., 1440
```

---

## 3. CAPA 3: Ingredient Library

### Contract 3.1: CompoundProfile

```python
@dataclass
class CompoundProfile:
    compound_id: str             # Único, snake_case
    name: str                    # Nombre legible
    category: str                # "stimulant"|"amino"|"vitamin"|"adaptogen"|"carbohydrate"|...
    
    # Farmacocinética
    pk_model: str                # "one_compartment"|"two_compartment"|"saturable"
    pk_params: Dict[str, float]  # Parámetros del modelo PK
    bioavailability: float       # 0-1
    
    # Farmacodinámica
    pd_model: str                # "emax"|"linear"|"threshold"|"none"
    pd_params: Dict[str, float]
    target_system: str           # "glucose"|"caffeine"|"cortisol"|...
    
    # Límites
    max_single_dose: float
    max_daily_dose: float
    dose_unit: str               # "mg"|"g"|"mcg"
    
    # Evidencia
    evidence_level: str          # "high"|"medium"|"low"|"theoretical"
    primary_sources: List[str]   # DOIs o referencias
    
# CONTRATO
- compound_id DEBE ser único en la librería
- pk_params DEBE contener los parámetros requeridos para pk_model
- pd_params DEBE contener los parámetros requeridos para pd_model
- bioavailability DEBE estar en [0, 1]
```

### Contract 3.2: IngredientLibrary

```python
class IngredientLibrary:
    def __init__(self, json_path: str)
    
    def get_compound(self, compound_id: str) -> CompoundProfile
    def list_compounds(self, category: Optional[str] = None) -> List[str]
    def get_interaction(self, compound_a: str, compound_b: str) -> Optional[Interaction]
    
# CONTRATO
- get_compound() lanza KeyError si no existe
- list_compounds() retorna IDs, no objetos completos
- get_interaction() retorna None si no hay interacción definida
```

### Contract 3.3: Interaction

```python
@dataclass
class Interaction:
    compound_a: str
    compound_b: str
    interaction_type: str    # "synergy"|"antagonism"|"absorption"|"metabolism"
    
    # Efecto
    target_param: str        # Qué parámetro modifica
    modifier_type: str       # "multiply"|"add"|"replace"
    modifier_value: float    # El modificador
    
    # Condiciones
    dose_dependent: bool
    min_dose_a: Optional[float]
    min_dose_b: Optional[float]
    
    # Evidencia
    evidence_level: str
    source: str
    
# CONTRATO
- compound_a < compound_b (orden alfabético para evitar duplicados)
- modifier_type="multiply" implica modifier_value típicamente en [0.5, 2.0]
- modifier_type="add" implica modifier_value en unidades del target_param
```

---

## 4. CAPA 4: Interaction Engine

### Contract 4.1: InteractionGraph

```python
class InteractionGraph:
    def __init__(self, library: IngredientLibrary)
    
    def get_applicable_interactions(
        self,
        compounds_present: List[Tuple[str, float]],  # (compound_id, dose)
    ) -> List[Interaction]
    
    def apply_interactions(
        self,
        base_effects: Dict[str, float],
        interactions: List[Interaction]
    ) -> Dict[str, float]  # Efectos modificados

# CONTRATO
- get_applicable_interactions() solo retorna interacciones donde ambos compounds están presentes
- apply_interactions() aplica en orden: primero synergies, luego antagonisms
- El resultado NUNCA tiene valores negativos para parámetros que deben ser positivos
```

---

## 5. CAPA 5: Simulation Orchestrator

### Contract 5.1: DaySimulator

```python
class DaySimulator:
    def __init__(
        self,
        person: VirtualPerson,
        library: IngredientLibrary,
        interaction_graph: InteractionGraph
    )
    
    def simulate(
        self,
        timeline: Timeline,
        dt_minutes: float = 1.0
    ) -> DaySimulationResult

@dataclass
class DaySimulationResult:
    person_id: str
    timeline: Timeline
    states: List[PhysiologicalState]  # Uno por timestep
    
    # Time series (1440 puntos para 24h con dt=1)
    time_minutes: np.ndarray
    glucose_curve: np.ndarray
    insulin_curve: np.ndarray
    caffeine_curve: np.ndarray
    alertness_curve: np.ndarray
    # ... otros sistemas
    
    # Métricas calculadas
    metrics: Dict[str, float]
    
    # Metadata
    is_valid: bool
    warnings: List[str]

# CONTRATO
- states tiene len = 1440/dt_minutes + 1
- Todas las curvas tienen la misma longitud que time_minutes
- metrics incluye al menos las métricas core definidas
```

### Contract 5.2: PopulationSimulator

```python
class PopulationSimulator:
    def simulate(
        self,
        population: List[VirtualPerson],
        timeline: Timeline,  # Mismo timeline para todos
        config: SimulationConfig
    ) -> PopulationSimulationResult

@dataclass
class PopulationSimulationResult:
    n_individuals: int
    n_valid: int
    
    # Percentiles de curvas (p5, p25, p50, p75, p95)
    time_minutes: np.ndarray
    glucose_percentiles: Dict[str, np.ndarray]
    alertness_percentiles: Dict[str, np.ndarray]
    # ...
    
    # Estadísticas de métricas
    metrics_stats: Dict[str, Dict[str, float]]  # {metric: {mean, std, p10, p90}}
    
    # Risk analysis
    risk_analysis: Dict[str, float]  # {risk_name: percentage}
    
    # Subgroup analysis
    subgroup_analysis: Dict[str, Dict[str, Any]]

# CONTRATO
- Mismo contrato que PopulationResults actual pero extendido para 24h
```

---

## 6. CAPA 6: Output

### Contract 6.1: ClaimAnalyzer

```python
class ClaimAnalyzer:
    def analyze(
        self,
        results: PopulationSimulationResult,
        claims: List[str]  # ["sustained_energy", "no_crash", "mental_focus"]
    ) -> Dict[str, ClaimAnalysis]

@dataclass
class ClaimAnalysis:
    claim_id: str
    claim_text: str
    
    # Resultado
    is_defensible: bool
    confidence: float  # 0-1
    responder_percentage: float
    
    # Evidencia
    supporting_metrics: Dict[str, float]
    methodology: str
    
    # Regulatorio
    efsa_compatible: bool
    fda_compatible: bool
    suggested_wording: str

# CONTRATO
- is_defensible=True solo si responder_percentage > 50% Y confidence > 0.7
- efsa_compatible requiere claim en lista aprobada EFSA
```

---

## 7. VALIDACIÓN DE CONTRATOS

Todos los contratos se validan con tests en `tests/integration/test_contracts.py`:

```python
def test_simulation_result_contract():
    """SimulationResult cumple su contrato."""
    result = model.simulate(input)
    
    # time_points monotónicamente creciente
    assert np.all(np.diff(result.time_points) > 0)
    
    # time_points empieza en 0
    assert result.time_points[0] == 0.0
    
    # Channels tienen longitud correcta
    for name, channel in result.channels.items():
        assert len(channel) == len(result.time_points)
    
    # Metrics tiene is_valid
    assert "is_valid" in result.metrics or "is_sim_valid" in result.metadata
```

---

## CHANGELOG

| Fecha | Versión | Cambio |
|-------|---------|--------|
| 2025-01-04 | 2.0 | Creación inicial para Camino B |
