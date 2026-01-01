# MODULUS - Quick Start Guide

Welcome to MODULUS! This guide will get you up and running in 5 minutes.

## Prerequisites

- Python 3.11+ (you have 3.12.3 ✓)
- Git (installed ✓)
- Basic command line familiarity

## Setup (5 minutes)

### Step 1: Navigate to Project
```bash
cd modulus
```

### Step 2: Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

This will install:
- NumPy, SciPy, Pandas (scientific computing)
- FastAPI (web framework)
- Matplotlib (visualization)
- ReportLab (PDF generation)
- Pytest (testing)
- And 15+ other packages

**Expected time:** 2-3 minutes

### Step 4: Verify Installation
```bash
python scripts/setup.py
```

You should see:
```
✓ Python 3.12.3 detected
✓ Git installed
✓ Directory Structure verified
✓ Reference Data validated
✓ Dependencies installed

Phase 0 Setup Complete! ✅
```

## Project Structure

```
modulus/
├── README.md                 ← Start here for overview
├── PHASE_0_COMPLETE.md      ← Detailed completion checklist  
├── PHASE_0_SUMMARY.md       ← This summary
├── requirements.txt         ← Python dependencies
│
├── data/
│   └── reference/           ← Scientific reference data
│       ├── glycemic_index.csv         (60+ foods)
│       ├── population_params.json     (NHANES data)
│       └── safety_thresholds.json     (Safety limits)
│
├── src/                     ← Source code (start coding here!)
│   ├── core/models/         ← Implement models here
│   │   └── base.py          ← Base classes (already done)
│   ├── core/population/     ← Population generator
│   ├── analysis/            ← Statistical analysis
│   └── reporting/           ← PDF generation
│
├── tests/                   ← Tests (write as you code)
└── scripts/
    └── setup.py             ← Validation script
```

## What to Build Next (Phase 1)

### Priority 1: Glucose Model (Days 3-4)
File: `src/core/models/glucose.py`

Implement the Dalla Man glucose-insulin model:
- Read the parameters from `data/reference/population_params.json`
- Use `scipy.integrate.odeint` for ODE solving
- Inherit from `BaseModel` in `base.py`
- Target: Predict blood glucose response to meals

**Key equations available in:** Project knowledge (Dalla Man et al. 2007)

### Priority 2: Caffeine Model (Day 5)
File: `src/core/models/caffeine.py`

Implement 1-compartment pharmacokinetic model:
- Simpler than glucose (analytical solution, no ODE)
- Parameters in `population_params.json`
- Genotype effects (CYP1A2: slow/normal/fast)
- Target: Predict plasma caffeine and alertness

### Priority 3: Population Generator (Days 6-7)
File: `src/core/population/generator.py`

Generate 1,000 virtual individuals:
- Use Latin Hypercube Sampling (scipy.stats.qmc)
- Sample from distributions in `population_params.json`
- Create `PersonParameters` objects (from `base.py`)
- Handle correlations (e.g., BMI ↔ insulin sensitivity)

## Reference Data Files

### Glycemic Index Database
**File:** `data/reference/glycemic_index.csv`
**Use for:** Looking up GI values for different foods
**Example:**
```python
import pandas as pd
gi_data = pd.read_csv('data/reference/glycemic_index.csv')
gi_data[gi_data['food_item'] == 'Banana']
# Returns: GI=51, GL=13, 25g carbs per 120g serving
```

### Population Parameters
**File:** `data/reference/population_params.json`
**Use for:** Sampling virtual individuals and model parameters
**Example:**
```python
import json
with open('data/reference/population_params.json') as f:
    params = json.load(f)

# Get Dalla Man glucose model parameters
glucose_params = params['dalla_man_parameters']
Vg_mean = glucose_params['Vg']['mean']  # 1.88 dL/kg
```

### Safety Thresholds
**File:** `data/reference/safety_thresholds.json`
**Use for:** Flagging dangerous glucose/caffeine levels
**Example:**
```python
import json
with open('data/reference/safety_thresholds.json') as f:
    safety = json.load(f)

# Check if glucose is in danger zone
if glucose_peak > 200:  # mg/dL
    # Severe hyperglycemia!
    flag = safety['glucose_thresholds']['severe_hyperglycemia']
```

## Testing

Write tests as you code:

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_glucose.py

# Run with coverage
pytest --cov=src tests/
```

## Development Workflow

1. **Create a new branch:**
   ```bash
   git checkout -b feature/glucose-model
   ```

2. **Code with tests:**
   - Write function in `src/`
   - Write test in `tests/unit/`
   - Run `pytest` to verify

3. **Validate against literature:**
   - Compare outputs to published data
   - Document correlation coefficients
   - Aim for r > 0.65

4. **Commit and push:**
   ```bash
   git add .
   git commit -m "Implement Dalla Man glucose model"
   git push origin feature/glucose-model
   ```

## Scientific References

All model equations and parameters are from these papers:

1. **Dalla Man C, et al. (2007)**  
   "Meal Simulation Model of the Glucose-Insulin System"  
   IEEE Trans Biomed Eng, 54(10):1740-1749  
   → Available in project knowledge

2. **Blanchard J, Sawers SJA (1983)**  
   "Comparative Pharmacokinetics of Caffeine in Young and Elderly Men"  
   J Pharmacokinet Biopharm, 11(2):109-126  
   → Available in project knowledge

3. **CDC NHANES (2017-2020)**  
   National Health and Nutrition Examination Survey  
   → Summarized in `population_params.json`

## Common Commands

```bash
# Activate virtual environment
source venv/bin/activate

# Install new package
pip install package_name
pip freeze > requirements.txt

# Run validation
python scripts/setup.py

# Format code
black src/
isort src/

# Lint code  
flake8 src/

# Run tests
pytest

# Check test coverage
pytest --cov=src --cov-report=html
```

## Getting Help

1. **README.md** - Project overview and architecture
2. **PHASE_0_COMPLETE.md** - Detailed setup checklist
3. **src/core/models/base.py** - See how to structure models
4. **Project knowledge** - Scientific papers with all equations

## Next Steps

1. ✅ Environment set up
2. ✅ Reference data loaded
3. ⏭️ **Start coding!** Begin with `src/core/models/glucose.py`

### Your First Task:
Create `src/core/models/glucose.py` and implement:
```python
from .base import BaseModel, ModelParameters, SimulationResult
from dataclasses import dataclass
import numpy as np
from scipy.integrate import odeint

@dataclass
class GlucoseModelParameters(ModelParameters):
    Vg: float  # Distribution volume
    k1: float  # Rate parameter
    k2: float  # Rate parameter
    # ... add all Dalla Man parameters

class GlucoseModel(BaseModel):
    def simulate(self, inputs, duration, time_step=1.0):
        # Implement ODE system
        # Return SimulationResult
        pass
```

**Target:** By end of Day 4, you should be able to:
```python
model = GlucoseModel(params)
result = model.simulate({'carbs_g': 50}, duration=240)
plt.plot(result.time_points, result.values)
# Should show glucose rising to ~140 mg/dL at 45 min, returning to baseline by 240 min
```

---

**Ready? Let's build MODULUS! 🚀**

*Any questions? Check the comprehensive documentation in README.md*
