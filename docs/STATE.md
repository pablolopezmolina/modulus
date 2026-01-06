# MODULUS — Development State
# Last Updated: 2025-01-04
#
# ⚠️  ACTUALIZAR DESPUÉS DE CADA SESIÓN DE DESARROLLO
# ⚠️  EL LLM DEBE LEER ESTO PARA SABER QUÉ ESTÁ HECHO
#
# 📌 VERSIÓN: 3.0 (Decision & Compliance OS)
# 📌 OBJETIVO: Pack 1 vendible (€50k) en Semana 8

## RESUMEN EJECUTIVO

```
FASE 0 (Anti-Frankenstein): ░░░░░░░░░░░░░░░░░░░░   0% 🔨 SIGUIENTE
FASE 1 (24h Engine):        ░░░░░░░░░░░░░░░░░░░░   0%
FASE 2 (Pack 1 - €50k):     ░░░░░░░░░░░░░░░░░░░░   0%
FASE 3 (Pack 2 - €250k):    ░░░░░░░░░░░░░░░░░░░░   0%
FASE 4 (Optimization):      ░░░░░░░░░░░░░░░░░░░░   0%
FASE 5 (Pack 3 - €500k):    ░░░░░░░░░░░░░░░░░░░░   0%

TOTAL PROGRESO:             ~15% (Capa 1 Foundation heredada de v1)
```

---

## CÓDIGO HEREDADO DE V1 (REUTILIZABLE)

Estos módulos fueron construidos en la versión anterior y están **100% funcionales**.
Deben integrarse en la nueva arquitectura sin reescribir.

### ✅ Modelos Fisiológicos (Capa 1 - Foundation)

| Módulo | Archivo | Estado | Notas |
|--------|---------|--------|-------|
| DallaManModel | `src/core/models/glucose.py` | ✅ Completo | 12 estados ODE, validado |
| EliteCaffeineModel | `src/core/models/caffeine.py` | ✅ Completo | PK + genotipos CYP1A2 |
| PhysiologicalModel (base) | `src/core/models/base.py` | ✅ Completo | Clase abstracta |

### ✅ Población (Capa 1 - Foundation)

| Módulo | Archivo | Estado | Notas |
|--------|---------|--------|-------|
| VirtualPerson | `src/core/population/person.py` | ✅ Completo | Frozen dataclass |
| PopulationGenerator | `src/core/population/generator.py` | ✅ Completo | LHS, correlaciones |
| Distributions | `src/core/population/distributions.py` | ✅ Completo | NHANES data |

### ✅ Engine V1

| Módulo | Archivo | Estado | Notas |
|--------|---------|--------|-------|
| SimulationEngine | `src/core/engine.py` | ✅ Completo | Single-event, streaming |
| Adapters | `src/core/adapters.py` | ✅ Completo | MealEffectConfig |

### ✅ API V1

| Módulo | Archivo | Estado | Notas |
|--------|---------|--------|-------|
| FastAPI | `src/api/main.py` | ✅ Completo | /simulate, /ab-test, /health |

### ✅ Datos de Referencia

| Archivo | Estado | Notas |
|---------|--------|-------|
| `data/reference/population_params.json` | ✅ Completo | 242 líneas, NHANES |
| `data/reference/glycemic_index.csv` | ✅ Existe | Índices glicémicos |

---

## FASE 0: ANTI-FRANKENSTEIN 🔨

### Sesión 0.1: Contratos Ejecutables
```
[ ] src/core/contracts/__init__.py
[ ] src/core/contracts/events.py
[ ] src/core/contracts/state.py
[ ] src/core/contracts/results.py
[ ] tests/unit/test_contracts.py
```

### Sesión 0.2: CI Local
```
[ ] Makefile
[ ] requirements-dev.txt
[ ] tests/integration/test_dependency_rules.py
[ ] pyproject.toml
```

### Sesión 0.3: Golden Scenarios Base
```
[ ] tests/golden/__init__.py
[ ] tests/golden/test_gs01_ogtt.py
[ ] tests/golden/test_gs02_coffee.py
[ ] tests/golden/test_gs10_reproducibility.py
```

---

## FASE 1: 24H ENGINE 🔨

### Semana 1: Timeline
```
[ ] src/core/timeline/__init__.py
[ ] src/core/timeline/event.py
[ ] src/core/timeline/timeline.py
[ ] tests/unit/test_event.py
[ ] tests/unit/test_timeline.py
```

### Semana 2: State + Integrator
```
[ ] src/core/state/__init__.py
[ ] src/core/state/state.py
[ ] src/core/state/integrator.py
[ ] tests/unit/test_state.py
[ ] tests/unit/test_integrator.py
```

### Semana 3: DaySimulator + PDF v0
```
[ ] src/core/simulation/__init__.py
[ ] src/core/simulation/day_simulator.py
[ ] src/analysis/__init__.py
[ ] src/analysis/metrics.py
[ ] src/reporting/__init__.py
[ ] src/reporting/pdf_generator.py
[ ] src/reporting/charts.py
```

---

## FASE 2: PACK 1 (€50k) 🔨

### Semana 4: Ingredients
```
[ ] src/core/compounds/__init__.py
[ ] src/core/compounds/profile.py
[ ] src/core/compounds/library.py
[ ] src/core/compounds/formulation.py
[ ] data/reference/ingredients.json (8 compuestos)
```

### Semana 5: Population + Risk
```
[ ] src/core/simulation/population_day_simulator.py
[ ] src/analysis/risk.py
```

### Semana 6: Decision
```
[ ] src/analysis/decision.py
[ ] src/analysis/claims.py
```

### Semana 7: PDF v1
```
[ ] src/reporting/pdf_generator.py (extendido a 20 pág)
[ ] src/reporting/charts.py (más gráficos)
```

---

## FASE 3: PACK 2 (€250k) 🔨

### Semana 8: Ingredients + Interactions
```
[ ] data/reference/ingredients.json (15 compuestos)
[ ] src/core/interactions/__init__.py
[ ] src/core/interactions/interaction.py
[ ] src/core/interactions/graph.py
[ ] data/reference/interactions.json
```

### Semana 9: Evidence
```
[ ] src/analysis/evidence.py
[ ] src/reporting/bundle.py
```

### Semana 10: Advanced Features
```
[ ] src/analysis/risk.py (6 segmentos)
[ ] src/analysis/comparison.py
[ ] src/reporting/certificate.py
```

### Semana 11: PDF v2
```
[ ] src/reporting/pdf_generator.py (40+ pág)
```

---

## ARCHIVOS DE CONFIGURACIÓN

| Archivo | Estado | Notas |
|---------|--------|-------|
| `data/reference/population_params.json` | ✅ | Completo |
| `data/reference/ingredients.json` | ❌ | Por crear |
| `data/reference/interactions.json` | ❌ | Por crear |
| `data/reference/glycemic_index.csv` | ✅ | Existe |
| `Makefile` | ❌ | Por crear |
| `requirements-dev.txt` | ❌ | Por crear |
| `pyproject.toml` | ❌ | Por crear |

---

## TESTS

| Suite | Estado | Cobertura |
|-------|--------|-----------|
| `tests/unit/` | ⚠️ | Parcial (v1) |
| `tests/integration/` | ❌ | Por crear |
| `tests/golden/` | ❌ | Por crear |
| `tests/integration/test_contracts.py` | ❌ | Por crear |
| `tests/integration/test_dependency_rules.py` | ❌ | Por crear |

---

## ESTRUCTURA DE CARPETAS OBJETIVO

```
modulus/
├── docs/
│   ├── ARCHITECTURE.md      ✅
│   ├── CONTRACTS.md         ✅
│   ├── STATE.md             ✅ (este archivo)
│   ├── ROADMAP.md           ✅
│   ├── DECISIONS.md         ✅
│   ├── MASTER_PROMPT.md     ✅
│   ├── GOLDEN_SCENARIOS.md  ✅
│   ├── BUSINESS_MODEL.md    ✅
│   └── Makefile             ✅ (template)
│
├── data/
│   └── reference/
│       ├── population_params.json  ✅
│       ├── glycemic_index.csv      ✅
│       ├── ingredients.json        ❌
│       └── interactions.json       ❌
│
├── src/
│   ├── core/
│   │   ├── models/          ✅ (glucose, caffeine, base)
│   │   ├── population/      ✅ (person, generator, distributions)
│   │   ├── timeline/        ❌ (event, timeline)
│   │   ├── state/           ❌ (state, integrator)
│   │   ├── compounds/       ❌ (profile, library, formulation)
│   │   ├── interactions/    ❌ (interaction, graph)
│   │   ├── simulation/      ❌ (day_simulator, population_day)
│   │   ├── contracts/       ❌ (events, state, results)
│   │   ├── engine.py        ✅
│   │   └── adapters.py      ✅
│   │
│   ├── analysis/            ❌
│   │   ├── metrics.py
│   │   ├── risk.py
│   │   ├── decision.py
│   │   ├── claims.py
│   │   ├── evidence.py
│   │   ├── comparison.py
│   │   └── recommendations.py
│   │
│   ├── reporting/           ❌
│   │   ├── pdf_generator.py
│   │   ├── charts.py
│   │   ├── certificate.py
│   │   └── bundle.py
│   │
│   └── api/
│       └── main.py          ✅
│
└── tests/
    ├── unit/                ⚠️
    ├── integration/         ❌
    └── golden/              ❌
```

---

## PRÓXIMA SESIÓN

**FASE 0, Sesión 0.1: Contratos Ejecutables**

```
OBJETIVO: Crear contratos Pydantic para Event, PhysiologicalState, SimulationResult

ARCHIVOS A CREAR:
- src/core/contracts/__init__.py
- src/core/contracts/events.py
- src/core/contracts/state.py
- src/core/contracts/results.py
- tests/unit/test_contracts.py

ARCHIVOS NO TOCAR:
- src/core/models/* (ya estable)
- src/core/population/* (ya estable)
- src/core/engine.py (ya estable)

CRITERIOS DE ÉXITO:
- Event rechaza timestamp <0 o >1440
- PhysiologicalState rechaza glucose NaN o <0
- Todos los campos con tipos estrictos
- Tests pasan
```

---

## CHANGELOG

| Fecha | Sesión | Cambios |
|-------|--------|---------|
| 2025-01-04 | - | Estado inicial v3.0. Capa 1 heredada de v1. |
