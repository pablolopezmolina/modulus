# MODULUS — Roadmap v3.0 (Decision & Compliance OS)
# Last Updated: 2025-01-04
#
# VISIÓN: Construir el "Decision & Compliance OS" de la industria de suplementos
# MÉTODO: LLM-driven development con arquitectura estricta
#
# PAQUETES COMERCIALES:
# - Pack 1 (€50k): Protocol Assessment → vendible en Fase 2
# - Pack 2 (€150-250k): Enterprise Risk & Compliance → vendible en Fase 3
# - Pack 3 (€250-500k/año): Strategic Partnership + Powered By → vendible en Fase 5
#
# ============================================================================

## RESUMEN EJECUTIVO

```
┌─────────────────────────────────────────────────────────────────────────┐
│  FASE 0 (1 semana)     │ Anti-Frankenstein: CI, contratos, tests      │
│  FASE 1 (3 semanas)    │ 24h Engine + PDF v0 → Demo para credibilidad │
│  FASE 2 (4 semanas)    │ Pack 1 vendible: Decision Page + Risk Map    │ ← €50k
│  FASE 3 (4 semanas)    │ Pack 2 vendible: Evidence + Certificate      │ ← €150-250k
│  FASE 4 (3 semanas)    │ Optimization + A/B Comparison                │
│  FASE 5 (4 semanas)    │ Pack 3: Consumer Web App + Real-time API     │ ← €250-500k/año
└─────────────────────────────────────────────────────────────────────────┘

TOTAL: ~19 semanas para producto completo
Pack 1 vendible: Semana 8
Pack 2 vendible: Semana 12
Pack 3 vendible: Semana 19
```

---

## FASE 0: SISTEMA ANTI-FRANKENSTEIN (1 semana, 3-5 sesiones)

**Objetivo:** Que la consistencia sea automática, no disciplina humana

### Sesión 0.1: Contratos Ejecutables con Pydantic
```
Archivos a crear:
[ ] src/core/contracts/__init__.py
[ ] src/core/contracts/events.py      # Event con validación
[ ] src/core/contracts/state.py       # PhysiologicalState con validación
[ ] src/core/contracts/results.py     # SimulationResult con validación

Tests a crear:
[ ] tests/unit/test_contracts.py

Criterios de éxito:
[ ] Event rechaza timestamp negativo
[ ] PhysiologicalState rechaza glucosa <0 o NaN
[ ] Todos los campos tienen tipos estrictos
```

### Sesión 0.2: CI Local + Dependency Rules
```
Archivos a crear:
[ ] Makefile (targets: lint, typecheck, test, check)
[ ] requirements-dev.txt
[ ] tests/integration/test_dependency_rules.py
[ ] pyproject.toml o setup.cfg (configuración de herramientas)

Criterios de éxito:
[ ] `make check` ejecuta lint + typecheck + tests
[ ] Test falla si core/ importa de api/ o reporting/
[ ] Todo pasa en <2 minutos
```

### Sesión 0.3: Golden Scenarios Base (3 escenarios)
```
Archivos a crear:
[ ] tests/golden/__init__.py
[ ] tests/golden/test_gs01_ogtt.py         # Glucosa sola
[ ] tests/golden/test_gs02_coffee.py       # Cafeína sola
[ ] tests/golden/test_gs10_reproducibility.py  # Determinismo

Criterios de éxito:
[ ] Los 3 escenarios pasan con código actual (v1)
[ ] Tolerancias definidas y documentadas
[ ] Cualquier cambio que rompa estos tests es bug
```

**GATE FASE 0:**
```
[ ] `make check` pasa en <2 minutos
[ ] Contratos Pydantic validan inputs/outputs
[ ] 3 golden scenarios pasan
[ ] Import rules verificadas automáticamente
```

---

## FASE 1: 24H ENGINE + PDF v0 (3 semanas, ~10 sesiones)

**Objetivo:** Simular un día completo y generar PDF básico
**Entregable:** Demo de credibilidad para LinkedIn/networking

### Semana 1: Timeline + Event

#### Sesión 1.1: Event (dataclass + validación)
```
Archivos a crear:
[ ] src/core/timeline/__init__.py
[ ] src/core/timeline/event.py

Especificación:
- @dataclass(frozen=True) Event
- Campos: timestamp_minutes, event_type, payload
- Tipos: "ingestion", "meal", "exercise", "sleep"
- Validación: timestamp en [0, 1440], tipos válidos
- Métodos: to_dict(), from_dict()

Tests:
[ ] tests/unit/test_event.py
```

#### Sesión 1.2: Timeline (inmutable, ordenada)
```
Archivos a crear:
[ ] src/core/timeline/timeline.py

Especificación:
- class Timeline (inmutable)
- Mantiene eventos ordenados por timestamp
- add_event() → nueva Timeline
- get_events_in_range(start, end) → List[Event]
- validate() → bool
- to_json() / from_json()

Tests:
[ ] tests/unit/test_timeline.py
```

### Semana 2: State + Integrator

#### Sesión 2.1: PhysiologicalState
```
Archivos a crear:
[ ] src/core/state/__init__.py
[ ] src/core/state/state.py

Especificación:
- @dataclass(frozen=True) PhysiologicalState
- Campos principales:
  * timestamp_minutes: float
  * glucose_plasma_mg_dl: float
  * insulin_plasma_mu_l: float
  * caffeine_plasma_mg_l: float
  * alertness_score: float (0-100)
  * is_fasted: bool
  * hours_since_last_meal: float
- Validación: todos los valores en rangos fisiológicos
- Factory: create_fasted_state(person) → PhysiologicalState

Tests:
[ ] tests/unit/test_state.py
```

#### Sesión 2.2: StateIntegrator (conecta modelos existentes)
```
Archivos a crear:
[ ] src/core/state/integrator.py

Especificación:
- class StateIntegrator
- __init__(person, glucose_model, caffeine_model)
- step(current_state, events, dt_minutes) → new_state
- Usa DallaManModel y EliteCaffeineModel existentes
- Maneja eventos de tipo "meal" y "ingestion"

Tests:
[ ] tests/unit/test_integrator.py

Golden scenarios que deben pasar:
[ ] GS01 (OGTT) - glucosa sola
[ ] GS02 (Coffee) - cafeína sola
```

#### Sesión 2.3: StateIntegrator 24h
```
Archivos a modificar:
[ ] src/core/state/integrator.py (añadir simulate_timeline)

Especificación:
- simulate_timeline(initial_state, timeline, dt=1.0) → List[PhysiologicalState]
- Itera sobre 1440 minutos (24h)
- Aplica eventos cuando corresponde
- Retorna lista de estados (1 por minuto)

Tests:
[ ] tests/unit/test_integrator_24h.py

Golden scenario nuevo:
[ ] GS05 (Full Day) - múltiples eventos
```

### Semana 3: DaySimulator + PDF v0

#### Sesión 3.1: DaySimulator
```
Archivos a crear:
[ ] src/core/simulation/__init__.py
[ ] src/core/simulation/day_simulator.py

Especificación:
- class DaySimulator
- __init__(person)
- simulate(timeline) → DaySimulationResult
- DaySimulationResult contiene:
  * time_minutes: np.ndarray (1440 puntos)
  * glucose_curve: np.ndarray
  * caffeine_curve: np.ndarray
  * alertness_curve: np.ndarray
  * metrics: Dict[str, float]
  * is_valid: bool

Tests:
[ ] tests/unit/test_day_simulator.py
```

#### Sesión 3.2: Métricas Básicas
```
Archivos a crear:
[ ] src/analysis/__init__.py
[ ] src/analysis/metrics.py

Métricas a implementar:
- glucose_peak, glucose_time_to_peak, glucose_auc
- caffeine_peak, caffeine_half_life
- alertness_peak, alertness_duration_above_60
- time_above_glucose_140 (% del día)
- sleep_disruption_risk (caffeine >1mg/L at 22:00)

Tests:
[ ] tests/unit/test_metrics.py
```

#### Sesión 3.3: PDF Generator v0
```
Archivos a crear:
[ ] src/reporting/__init__.py
[ ] src/reporting/pdf_generator.py
[ ] src/reporting/charts.py

Especificación (PDF v0, 6-10 páginas):
- Página 1: Executive Summary
- Página 2-3: Curvas 24h (glucosa, cafeína, alertness)
- Página 4: Métricas principales
- Página 5: Warnings básicos
- Página 6: Methodology brief

Tests:
[ ] tests/unit/test_pdf_generator.py (genera sin errores)
```

**GATE FASE 1:**
```
[ ] Timeline + Events funcionan
[ ] StateIntegrator simula 24h correctamente
[ ] DaySimulator produce resultados válidos
[ ] Métricas básicas calculadas
[ ] PDF v0 se genera (6-10 páginas)
[ ] GS01, GS02, GS05, GS10 pasan
[ ] `make check` pasa
```

**HITO:** Video demo "Simulo un día completo" para LinkedIn

---

## FASE 2: PACK 1 VENDIBLE (4 semanas, ~12 sesiones)

**Objetivo:** Producto mínimo vendible a €50k
**Entregable:** Protocol Assessment completo

### Semana 4: Ingredient Library (15 compuestos)

#### Sesión 4.1: CompoundProfile + Library
```
Archivos a crear:
[ ] src/core/compounds/__init__.py
[ ] src/core/compounds/profile.py
[ ] src/core/compounds/library.py

Especificación:
- @dataclass CompoundProfile (validado)
- IngredientLibrary.get_compound(id) → CompoundProfile
- IngredientLibrary.list_compounds() → List[str]
```

#### Sesión 4.2: Ingredientes Tier 1 (8 compuestos impecables)
```
Archivos a crear:
[ ] data/reference/ingredients.json

Compuestos (con evidencia COMPLETA):
1. caffeine - ya modelado, documentar mejor
2. carbohydrate_glucose - ya modelado
3. carbohydrate_maltodextrin - GI alto
4. carbohydrate_palatinose - GI bajo
5. l_theanine - sinergista con cafeína
6. taurine - común en energy drinks
7. beta_alanine - pre-workout clásico
8. creatine_monohydrate - muy estudiado

Cada uno con: pk_params, pd_params, sources[], confidence
```

#### Sesión 4.3: Formulation System
```
Archivos a crear:
[ ] src/core/compounds/formulation.py

Especificación:
- class Ingredient(compound_id, amount, unit)
- class Formulation(name, ingredients[], form, serving_info)
- validate() → bool + List[warnings]
- to_timeline(base_time) → Timeline
```

### Semana 5: Population + Basic Risk

#### Sesión 5.1: PopulationDaySimulator
```
Archivos a crear:
[ ] src/core/simulation/population_day_simulator.py

Especificación:
- Reutiliza PopulationGenerator existente
- simulate(population, timeline) → PopulationDayResult
- Streaming aggregation (memoria O(1))
- Target: N=1000 en <30 segundos
```

#### Sesión 5.2: Basic Risk Map
```
Archivos a crear:
[ ] src/analysis/risk.py

Métricas de riesgo:
- pct_hyperglycemia (glucose >140)
- pct_severe_hyperglycemia (>180)
- pct_jitter_risk (caffeine >4mg/L)
- pct_sleep_disruption (caffeine >1mg/L at 22:00)
- pct_crash_risk (alertness drop >30% in 2h)

Segmentación básica (3 segmentos):
- by_bmi: normal, overweight, obese
- by_age: young (18-35), middle (36-55), older (56+)
- by_caffeine_sensitivity: slow, normal, fast
```

### Semana 6: Decision Page

#### Sesión 6.1: DecisionEngine
```
Archivos a crear:
[ ] src/analysis/decision.py

Especificación:
- class DecisionEngine
- analyze(population_results) → Decision
- Decision:
  * verdict: "GO" | "CAUTION" | "NO_GO"
  * confidence: float (0-1)
  * top_risks: List[Risk] (top 5)
  * top_segments_at_risk: List[Segment]
  * summary: str (2-3 oraciones)

Reglas de decisión:
- GO: <10% en cualquier riesgo alto
- CAUTION: 10-25% en algún riesgo
- NO_GO: >25% en algún riesgo alto
```

#### Sesión 6.2: Claim Defensibility (conservador)
```
Archivos a crear:
[ ] src/analysis/claims.py

Claims iniciales (no EFSA, solo defensibilidad):
- sustained_energy: alertness >60% for >4h
- no_crash: <10% experimenta drop >30%
- quick_onset: peak alertness <45min
- glucose_friendly: <15% hyperglycemia

Output:
- responder_percentage: float
- is_defensible: bool (>50% responders)
- confidence: float
- suggested_wording: str (conservador)
```

### Semana 7: PDF v1 (Pack 1 Complete)

#### Sesión 7.1: PDF v1 Completo
```
Archivos a modificar:
[ ] src/reporting/pdf_generator.py (extender)
[ ] src/reporting/charts.py (más gráficos)

PDF v1 (20 páginas):
1. Cover Page
2. Executive Summary (1 pág)
3. Decision Page - GO/CAUTION/NO_GO (1 pág)
4. Product Overview (1 pág)
5-6. Curvas 24h con percentiles (2 pág)
7-8. Risk Analysis + Risk Map (2 pág)
9-10. Segment Analysis (2 pág)
11-12. Claim Defensibility (2 pág)
13-14. Recommendations (2 pág)
15-16. Methodology Summary (2 pág)
17-18. Key Metrics Tables (2 pág)
19-20. Appendix: Glossary + References (2 pág)
```

#### Sesión 7.2: Integration Test Pack 1
```
Test end-to-end:
[ ] Formulation → Timeline → PopulationSim → Decision → PDF

Validar:
[ ] PDF se genera sin errores
[ ] Todas las secciones tienen contenido
[ ] Gráficos son legibles
[ ] Decision Page es clara
```

**GATE FASE 2:**
```
[ ] 8 ingredientes con evidencia completa
[ ] Population simulation N=1000 en <30s
[ ] Risk Map con 3 segmentos
[ ] Decision Page (Go/Caution/No-Go)
[ ] Claim defensibility básico
[ ] PDF v1 (20 páginas profesional)
[ ] GS01-GS06 pasan
[ ] `make check` pasa
```

**🎯 PACK 1 VENDIBLE: €50k**

---

## FASE 3: PACK 2 VENDIBLE (4 semanas, ~12 sesiones)

**Objetivo:** Enterprise Risk & Compliance (€150-250k)
**Entregable:** Evidence Bundle + Certificate + Comparison

### Semana 8: More Ingredients + Interactions

#### Sesión 8.1: Ingredientes Tier 2 (7 más = 15 total)
```
Añadir a ingredients.json:
9. citrulline_malate
10. tyrosine
11. alpha_gpc
12. vitamin_b6
13. vitamin_b12
14. magnesium_citrate
15. ashwagandha (adaptógeno)

Cada uno con: pk_params, pd_params, sources[], confidence
```

#### Sesión 8.2: Interaction Framework
```
Archivos a crear:
[ ] src/core/interactions/__init__.py
[ ] src/core/interactions/interaction.py
[ ] src/core/interactions/graph.py
[ ] data/reference/interactions.json

Interacciones clave (10):
1. caffeine + l_theanine → reduced_jitter (-50%)
2. caffeine + food → delayed_absorption (+30min Tmax)
3. carbs + protein → slower_absorption
4. carbs + fat → slower_absorption
5. carbs + fiber → reduced_peak (-15%)
6. creatine + carbs → enhanced_uptake
7. caffeine_high (>300mg) → increased_jitter
8. caffeine_afternoon (>14:00) → sleep_disruption
9. caffeine + caffeine (multiple) → additive
10. tyrosine + caffeine → enhanced_focus
```

### Semana 9: Evidence System

#### Sesión 9.1: Evidence Registry
```
Archivos a crear:
[ ] src/analysis/evidence.py

Especificación:
- class EvidenceRegistry
- Cada parámetro → source (DOI/DB) + confidence + notes
- generate_evidence_table() → para PDF
- export_citations() → BibTeX o lista

Actualizar ingredients.json:
- Añadir DOIs a todos los parámetros
- Añadir confidence level (high/medium/low)
```

#### Sesión 9.2: Reproducibility Bundle
```
Archivos a crear:
[ ] src/reporting/bundle.py

Especificación:
- class ReproducibilityBundle
- Contenido:
  * config.json (todos los inputs)
  * version: str (MODULUS version)
  * hash: str (SHA256 de inputs)
  * seed: int
  * timestamp: str
  * ingredient_versions: Dict
- export() → JSON file
- verify(bundle, results) → bool
```

### Semana 10: Advanced Features

#### Sesión 10.1: Full Risk Map (6 segmentos)
```
Archivos a modificar:
[ ] src/analysis/risk.py

Añadir segmentos:
- by_insulin_sensitivity: sensitive, normal, resistant
- by_activity_level: sedentary, moderate, active
- by_habitual_caffeine: naive, moderate, heavy

Risk Map completo:
- Matriz: segmento × riesgo
- Identificar "danger zones"
- Calcular % de población total en cada celda
```

#### Sesión 10.2: A/B Comparison Engine
```
Archivos a crear:
[ ] src/analysis/comparison.py

Especificación:
- class ComparisonEngine
- compare(results_a, results_b, ...) → Comparison
- Métricas comparadas:
  * Δ glucose_peak
  * Δ alertness_duration
  * Δ risk_scores
  * winner_by_metric: Dict[str, "A"|"B"|"TIE"]
- Statistical significance (si N suficiente)
```

#### Sesión 10.3: Modulus Protocol Certificate
```
Archivos a crear:
[ ] src/reporting/certificate.py

Especificación:
- class CertificateGenerator
- generate(results, decision) → PDF (1 página)
- Contenido:
  * "MODULUS PROTOCOL VERIFIED"
  * Product name
  * Verdict (GO/CAUTION)
  * Key metrics summary
  * Date + unique ID
  * QR code → link a verificación
```

### Semana 11: PDF v2 (Pack 2 Complete)

#### Sesión 11.1: PDF v2 Enterprise
```
PDF v2 (40-50 páginas):
- Todo de v1, más:
- Comparison section (si aplica)
- Full Risk Map visualization
- Evidence appendix (10+ páginas)
- Reproducibility info
- Certificate page

Diseño más profesional:
- Colores corporativos
- Gráficos mejorados
- Table of contents
```

#### Sesión 11.2: API Updates
```
Archivos a modificar:
[ ] src/api/main.py

Nuevos endpoints:
- POST /simulate-formulation (Formulation → Result)
- POST /compare (A vs B)
- GET /certificate/{id}
- GET /evidence/{id}
- GET /bundle/{id}
```

**GATE FASE 3:**
```
[ ] 15 ingredientes con evidencia completa
[ ] 10 interacciones modeladas
[ ] Evidence Registry con DOIs
[ ] Reproducibility Bundle funcional
[ ] Full Risk Map (6 segmentos)
[ ] A/B Comparison
[ ] Certificate generator
[ ] PDF v2 (40+ páginas)
[ ] GS01-GS09 pasan
[ ] `make check` pasa
```

**🎯 PACK 2 VENDIBLE: €150-250k**

---

## FASE 4: OPTIMIZATION (3 semanas)

**Objetivo:** Recomendaciones inteligentes y optimización

### Sesión 14.1: Recommendation Engine
```
Archivos a crear:
[ ] src/analysis/recommendations.py

Tipos de recomendaciones:
- Ingredient adjustment: "Reducir cafeína 200→150mg"
- Timing optimization: "Mejor antes de las 16:00"
- Addition suggestion: "Añadir L-Theanine 100mg"
- Label warning: "Añadir warning para sensibles a cafeína"

Cada recomendación con:
- expected_impact: Dict[metric, Δvalue]
- confidence: float
- evidence_summary: str
```

### Sesión 14.2: Simple Optimizer
```
Archivos a crear:
[ ] src/analysis/optimizer.py

Especificación:
- class FormulationOptimizer
- optimize(base_formula, objective, constraints) → List[Formulation]
- Objetivos: max_efficacy, min_risk, balanced
- Constraints: max_caffeine, max_cost, must_include, must_exclude
- Método: Grid search sobre variantes razonables
- Output: Top 3 fórmulas + comparison
```

---

## FASE 5: PACK 3 - POWERED BY (4 semanas)

**Objetivo:** Consumer-facing + Data flywheel
**Entregable:** Web app marca blanca + real-time API

### Sesiones 15.x: Consumer Web App
```
Archivos a crear:
[ ] src/webapp/__init__.py
[ ] src/webapp/app.py (FastAPI + templates)
[ ] src/webapp/templates/
[ ] src/webapp/static/

Especificación:
- Web app responsive (mobile-first)
- Marca blanca (colores/logo del cliente)
- Flow:
  1. User scans QR / clicks link
  2. Form: peso, hora despertar, hora entreno
  3. Output: timing óptimo, dosis ajustada, warnings
- <100ms response time
```

### Sesiones 16.x: Real-time Personalization API
```
Archivos a crear:
[ ] src/api/personalization.py

Endpoint:
POST /personalize
{
  "product_id": "xxx",
  "user": {
    "weight_kg": 75,
    "wake_time": "07:00",
    "activity_time": "18:00",
    "caffeine_sensitivity": "normal"
  }
}

Response:
{
  "optimal_timing": "17:15",
  "dosage_multiplier": 1.0,
  "warnings": [],
  "expected_effect": {...}
}

Requirements:
- <100ms latency
- Cached product profiles
- Simple user model (no full simulation)
```

### Sesiones 17.x: Analytics Dashboard
```
Para el cliente (marca):
- Cuántos usuarios usan la personalización
- Distribución de horarios de uso
- Feedback agregado
- Retention metrics
```

**GATE FASE 5:**
```
[ ] Consumer web app funcional
[ ] Real-time API <100ms
[ ] Analytics dashboard básico
[ ] Marca blanca configurable
```

**🎯 PACK 3 VENDIBLE: €250-500k/año**

---

## RESUMEN DE GATES Y ENTREGABLES

| Fase | Semanas | Gate | Entregable Comercial | Precio |
|------|---------|------|----------------------|--------|
| 0 | 1 | CI + Tests | - | - |
| 1 | 3 | 24h Engine + PDF v0 | Demo credibilidad | €0 |
| 2 | 4 | Decision + Risk + PDF v1 | **Pack 1** | **€50k** |
| 3 | 4 | Evidence + Certificate + PDF v2 | **Pack 2** | **€150-250k** |
| 4 | 3 | Optimization | Pack 2+ | - |
| 5 | 4 | Consumer App + API | **Pack 3** | **€250-500k/año** |

**Total: ~19 semanas**

---

## REGLAS PARA CADA SESIÓN

```
ANTES DE EMPEZAR:
1. [ ] Copiar MASTER_PROMPT.md al LLM
2. [ ] Pegar: ARCHITECTURE.md + CONTRACTS.md + STATE.md
3. [ ] Especificar la sesión de este ROADMAP
4. [ ] Listar archivos permitidos y NO tocar

DURANTE:
5. [ ] LLM escribe tests PRIMERO
6. [ ] LLM implementa
7. [ ] Verificar que no viola contratos
8. [ ] `make check` pasa

DESPUÉS:
9. [ ] Actualizar STATE.md
10. [ ] Marcar checkbox aquí
11. [ ] Git commit con mensaje descriptivo
```

---

## CHANGELOG

| Fecha | Versión | Cambio |
|-------|---------|--------|
| 2025-01-04 | 3.0 | Visión integrada: Decision OS + Packs comerciales |
