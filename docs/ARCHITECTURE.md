# MODULUS — Architecture Document
# Version: 3.0 (Decision & Compliance OS)
# Last Updated: 2025-01-04
# 
# ⚠️  ESTE DOCUMENTO ES LA FUENTE DE VERDAD
# ⚠️  TODO LLM DEBE LEERLO ANTES DE ESCRIBIR CÓDIGO
# ⚠️  NO MODIFICAR SIN REVISIÓN EXPLÍCITA
#
# 📌 LEER PRIMERO: BUSINESS_MODEL.md para entender el contexto de negocio

## 1. VISIÓN DEL PRODUCTO

MODULUS es el **"Decision & Compliance OS"** de la industria de suplementos.

**No vendemos simulaciones. Vendemos:**
- Reducción de riesgo (Go/No-Go en 48h)
- Aceleración de lanzamientos (de meses a días)
- Trazabilidad auditable (Evidence Bundle)
- Personalización al consumidor final (Powered By)

**El motor técnico** es un simulador metabólico 24h que predice cómo responde
el cuerpo humano a suplementos y alimentos a lo largo de un día completo.

**Pero el PRODUCTO** es el PDF/Decision Pack que permite a un Director de I+D
tomar una decisión de lanzamiento con confianza.

**Ejemplo de output (lo que el cliente COMPRA):**
```
┌─────────────────────────────────────────────────────────────────┐
│  MODULUS PROTOCOL ASSESSMENT                                    │
│  Product: "Energy Pro Max" by ClientCorp                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  DECISION: ⚠️  CAUTION - REFORMULATION RECOMMENDED              │
│                                                                 │
│  TOP RISKS:                                                     │
│  1. 23% sleep disruption (slow caffeine metabolizers)           │
│  2. 15% jitter risk (caffeine dose >300mg equivalent)           │
│  3. 8% glucose spike >160mg/dL (pre-diabetic segment)          │
│                                                                 │
│  RECOMMENDATIONS:                                               │
│  • Reduce caffeine 200→150mg: sleep risk -40%                   │
│  • Add L-Theanine 100mg: jitter risk -65%                       │
│  • Add label warning: "Not for caffeine-sensitive individuals"  │
│                                                                 │
│  CLAIM DEFENSIBILITY:                                           │
│  • "Sustained Energy" → 73% responders → DEFENSIBLE             │
│  • "No Crash" → 91% no crash → DEFENSIBLE                       │
│  • "Mental Focus" → 54% improvement → PARTIAL                   │
│                                                                 │
│  [Full report: 40 pages + Evidence Bundle + Reproducibility]    │
└─────────────────────────────────────────────────────────────────┘
```

**Paquetes comerciales:** €50k (Pack 1) → €250k (Pack 2) → €500k/año (Pack 3)
**Ver BUSINESS_MODEL.md para detalles completos.**

---

## 2. ARQUITECTURA DE ALTO NIVEL

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           MODULUS ENGINE v3.0                           │
│                     "Decision & Compliance OS"                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  CAPA 1: FOUNDATION (Ya construido ✅)                                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  • PhysiologicalModel (base abstracta)                          │   │
│  │  • DallaManModel (glucosa, 12 estados ODE)                      │   │
│  │  • EliteCaffeineModel (PK 1-compartimento)                      │   │
│  │  • VirtualPerson (individuo con parámetros)                     │   │
│  │  • PopulationGenerator (LHS, NHANES, correlaciones)             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    ▼                                    │
│  CAPA 2: TIMELINE ENGINE (Por construir 🔨)                            │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  • Timeline: Lista ordenada de eventos en 24h                   │   │
│  │  • Event: (timestamp, tipo, payload)                            │   │
│  │  • PhysiologicalState: Estado continuo del cuerpo               │   │
│  │  • StateIntegrator: Avanza el estado en el tiempo               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    ▼                                    │
│  CAPA 3: INGREDIENT LIBRARY (Por construir 🔨)                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  • IngredientLibrary: Base de datos de 15-20 compuestos         │   │
│  │  • CompoundProfile: PK/PD, límites, evidencia                   │   │
│  │  • Formulation: Producto = lista de ingredientes                │   │
│  │  • AbsorptionModelFactory: Genera curvas Ra según contexto      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    ▼                                    │
│  CAPA 4: INTERACTION ENGINE (Por construir 🔨)                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  • InteractionGraph: Mapa de sinergias/antagonismos             │   │
│  │  • SystemCoupling: Cross-talk entre sistemas fisiológicos       │   │
│  │  • EffectModifier: Aplica interacciones al estado               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    ▼                                    │
│  CAPA 5: SIMULATION ORCHESTRATOR (Por construir 🔨)                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  • DaySimulator: Orquesta simulación de 24h                     │   │
│  │  • PopulationSimulator: Ejecuta N gemelos digitales             │   │
│  │  • MetricsCalculator: Calcula métricas de negocio               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    ▼                                    │
│  CAPA 6: DECISION & ANALYSIS (Por construir 🔨) ⭐ CORE BUSINESS      │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  • DecisionEngine: Go / Caution / No-Go                         │   │
│  │  • RiskMapper: Segmentos + % en riesgo                          │   │
│  │  • ClaimAnalyzer: Defensibilidad de claims                      │   │
│  │  • RecommendationEngine: Sugerencias de mejora                  │   │
│  │  • EvidenceRegistry: Trazabilidad de fuentes                    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    ▼                                    │
│  CAPA 7: OUTPUT & DELIVERY (Por construir 🔨) ⭐ LO QUE SE VENDE      │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  • PDFGenerator: Reporte profesional (20-50 páginas)            │   │
│  │  • CertificateGenerator: "Modulus Protocol Verified"            │   │
│  │  • ReproducibilityBundle: JSON + hash + versión                 │   │
│  │  • ConsumerWebApp: Personalización real-time (Pack 3)           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**PRINCIPIO CLAVE:** Las Capas 1-5 son el "motor". Las Capas 6-7 son el "producto".
El cliente nunca ve las Capas 1-5. Solo ve el output de las Capas 6-7.

---

## 3. SISTEMAS FISIOLÓGICOS MODELADOS

### 3.1 Sistema de Glucosa (✅ Implementado)
- Modelo: Dalla Man 2007
- Estados: Gp, Gt, Ip, Il, Qsto1, Qsto2, Qgut, X, I1, Id, Ipo, Y
- Output: Curva de glucosa plasmática (mg/dL)

### 3.2 Sistema de Cafeína/Adenosina (✅ Implementado)
- Modelo: 1-compartimento PK + efecto Emax
- Estados: Concentración plasmática, ocupación receptores adenosina
- Output: Alertness score (0-100%)

### 3.3 Sistema de Aminoácidos (🔨 Por construir)
- Modelo: Absorción proteica multi-pool
- Estados: AA plasmáticos (esenciales, BCAAs)
- Output: Disponibilidad para síntesis muscular

### 3.4 Sistema de Cortisol/HPA (🔨 Por construir)
- Modelo: Ritmo circadiano + modulación por estrés/adaptógenos
- Estados: Cortisol plasmático, ACTH
- Output: Nivel de estrés, modulación por adaptógenos

### 3.5 Sistema de Creatina (🔨 Por construir)
- Modelo: Saturación fosfocreatina muscular
- Estados: PCr muscular, Cr plasmática
- Output: Capacidad de trabajo anaeróbico

### 3.6 Sistema de Energía Celular (🔨 Por construir)
- Modelo: ATP/ADP ratio simplificado
- Estados: Disponibilidad energética percibida
- Output: "Energy score" compuesto

---

## 4. ESTRUCTURA DE CARPETAS

```
modulus/
├── docs/
│   ├── ARCHITECTURE.md      # ESTE ARCHIVO (leer siempre)
│   ├── CONTRACTS.md         # Interfaces entre módulos
│   ├── STATE.md             # Estado actual del desarrollo
│   ├── DECISIONS.md         # Log de decisiones arquitectónicas
│   └── ROADMAP.md           # Fases con checkboxes
│
├── data/
│   └── reference/
│       ├── ingredients.json       # Librería de ingredientes
│       ├── interactions.json      # Matriz de interacciones
│       ├── population_params.json # Parámetros poblacionales
│       └── evidence/              # Papers y referencias
│
├── src/
│   ├── core/
│   │   ├── models/          # Modelos fisiológicos (Dalla Man, Caffeine, etc.)
│   │   ├── population/      # VirtualPerson, Generator
│   │   ├── state/           # PhysiologicalState, StateIntegrator [NUEVO]
│   │   ├── timeline/        # Timeline, Event [NUEVO]
│   │   ├── compounds/       # IngredientLibrary, Formulation [NUEVO]
│   │   ├── interactions/    # InteractionGraph, SystemCoupling [NUEVO]
│   │   └── engine.py        # Orquestador principal
│   │
│   ├── analysis/
│   │   ├── metrics.py       # Métricas de negocio [NUEVO]
│   │   ├── claims.py        # Análisis de claims [NUEVO]
│   │   └── optimizer.py     # Optimización de fórmulas [NUEVO]
│   │
│   ├── reporting/
│   │   └── pdf_generator.py # Generación de reportes [NUEVO]
│   │
│   └── api/
│       └── main.py          # FastAPI endpoints
│
└── tests/
    ├── unit/
    ├── integration/
    │   └── test_contracts.py  # Tests de contratos entre módulos
    └── validation/
        └── test_vs_literature.py  # Validación contra papers
```

---

## 5. PRINCIPIOS DE DISEÑO (INMUTABLES)

### 5.1 Separación de Concerns
- Cada sistema fisiológico es independiente
- Las interacciones se modelan en capa separada
- El estado es el "bus" de comunicación entre sistemas

### 5.2 Inmutabilidad del Estado
- PhysiologicalState es inmutable
- Cada step crea un NUEVO estado
- Esto permite debugging y reproducibilidad

### 5.3 Contratos Estrictos
- Las interfaces entre capas están definidas en CONTRACTS.md
- Un módulo NO puede cambiar la interfaz sin actualizar el contrato
- Tests automáticos validan que los contratos se cumplen

### 5.4 Evidence-Based Parameters
- TODO parámetro debe tener una fuente (paper, base de datos)
- La fuente se documenta en el código y en ingredients.json
- Nivel de confianza: "high", "medium", "low", "estimated"

### 5.5 Determinismo
- Misma seed + mismos inputs = mismos outputs
- SIEMPRE
- Tests de regresión lo validan

---

## 6. DEPENDENCIAS EXTERNAS

```
# Core científico
numpy>=1.24
scipy>=1.10
pandas>=2.0

# API
fastapi>=0.100
uvicorn>=0.22
pydantic>=2.0

# Reporting
matplotlib>=3.7
reportlab>=4.0

# Testing
pytest>=7.0
```

---

## 7. GLOSARIO

| Término | Definición |
|---------|------------|
| **Event** | Algo que ocurre en un momento: ingesta, comida, ejercicio |
| **Timeline** | Secuencia ordenada de Events en 24h |
| **PhysiologicalState** | Snapshot del estado del cuerpo en un instante |
| **System** | Un subsistema fisiológico (glucosa, cafeína, cortisol...) |
| **Compound** | Un ingrediente/sustancia con propiedades PK/PD |
| **Formulation** | Un producto = conjunto de Compounds |
| **Interaction** | Efecto de un Compound sobre otro |
| **Metric** | Valor calculado con significado de negocio |
| **Claim** | Afirmación regulatoria ("sustained energy") |

---

## 8. CÓMO USAR ESTE DOCUMENTO

### Para el desarrollador (humano):
1. Leer antes de cada sesión de desarrollo
2. Actualizar STATE.md después de cada sesión
3. NO modificar CONTRACTS.md sin revisión

### Para el LLM:
1. SIEMPRE leer ARCHITECTURE.md al inicio
2. SIEMPRE leer CONTRACTS.md antes de implementar
3. SIEMPRE verificar que el código nuevo cumple contratos
4. NUNCA cambiar interfaces sin actualizar CONTRACTS.md
5. ACTUALIZAR STATE.md con lo implementado
