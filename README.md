# MODULUS

**Decision & Compliance OS for the Supplements Industry**

MODULUS is an in-silico metabolic response simulator that predicts how different user populations will respond to supplements and functional foods over a 24-hour period.

## 🎯 What It Does

Instead of expensive clinical trials:
- **Input:** Product formulation (ingredients, doses, timing)
- **Output:** Risk assessment, efficacy predictions, regulatory claim defensibility

## 📦 Commercial Packages

| Package | Price | What You Get |
|---------|-------|--------------|
| **Pack 1: Protocol Assessment** | €50k | Go/No-Go decision, risk map, 20-page PDF |
| **Pack 2: Enterprise Risk & Compliance** | €150-250k | Evidence bundle, certificate, A/B comparison |
| **Pack 3: Powered By Modulus** | €250-500k/year | Consumer web app, real-time personalization |

## 🔬 Scientific Foundation

- **Glucose Model:** Dalla Man et al. (2007) - FDA-validated glucose-insulin dynamics
- **Caffeine Model:** 1-compartment PK with CYP1A2 genotype effects
- **Population:** NHANES-based virtual population with Latin Hypercube Sampling

## 🏗️ Project Structure

```
modulus/
├── docs/                    # Architecture & documentation
│   ├── ARCHITECTURE.md      # Technical vision
│   ├── CONTRACTS.md         # Module interfaces
│   ├── STATE.md             # Current development state
│   ├── ROADMAP.md           # Development plan
│   └── BUSINESS_MODEL.md    # Commercial strategy
│
├── src/
│   ├── core/
│   │   ├── models/          # Physiological models (glucose, caffeine)
│   │   ├── population/      # Virtual person generation
│   │   ├── timeline/        # 24h event timeline [TODO]
│   │   ├── state/           # Physiological state [TODO]
│   │   ├── compounds/       # Ingredient library [TODO]
│   │   └── simulation/      # Day simulator [TODO]
│   ├── analysis/            # Risk, decisions, claims [TODO]
│   ├── reporting/           # PDF generation [TODO]
│   └── api/                 # FastAPI endpoints
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── golden/              # Regression tests
│
└── data/reference/          # Static reference data
```

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run demo simulation
python scripts/demo_simulation.py

# Run API server
uvicorn src.api.main:app --reload

# Run tests
make check
```

## 📊 Current Status

See [docs/STATE.md](docs/STATE.md) for detailed development status.

**Completed:**
- ✅ Dalla Man glucose model (12-state ODE)
- ✅ Caffeine PK model with CYP1A2 genotypes
- ✅ Virtual population generator (NHANES-based)
- ✅ FastAPI endpoints

**In Progress:**
- 🔨 24h Timeline Engine
- 🔨 Decision Page generation
- 🔨 PDF report generation

## 📄 License

Proprietary - All rights reserved

## 📧 Contact

[Your contact info]
