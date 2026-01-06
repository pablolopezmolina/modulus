# MODULUS — Golden Scenarios
# 
# 10 escenarios canónicos que SIEMPRE deben pasar.
# Si alguno falla después de un cambio, algo se rompió.
# 
# Ejecutar con: pytest tests/golden/ -v
# ============================================================================

## PROPÓSITO

Estos escenarios son "contratos con la realidad". Cada uno representa un caso de uso real con valores esperados validados contra literatura o sentido común fisiológico.

Si alguien (humano o LLM) hace un cambio que rompe un golden scenario, el cambio es INCORRECTO hasta que se demuestre lo contrario.

---

## SCENARIO 1: Glucose Only - Standard OGTT
**Archivo:** `tests/golden/test_gs01_ogtt.py`

**Input:**
```python
timeline = Timeline([
    Event(timestamp_minutes=0, event_type="meal", payload={
        "carbs_g": 75,
        "protein_g": 0,
        "fat_g": 0,
        "fiber_g": 0,
        "glycemic_index": 100  # Pure glucose
    })
])
person = VirtualPerson.create_reference()  # 78kg, healthy, normal sensitivity
```

**Expected Output (tolerances):**
```python
# Glucose curve
assert 140 <= peak_glucose <= 180  # mg/dL (OGTT normal response)
assert 30 <= time_to_peak <= 60    # minutes
assert 80 <= glucose_at_240min <= 110  # Back to baseline

# No caffeine
assert caffeine_peak == 0
```

**Source:** Dalla Man 2007, standard OGTT protocol

---

## SCENARIO 2: Caffeine Only - Morning Coffee
**Archivo:** `tests/golden/test_gs02_coffee.py`

**Input:**
```python
timeline = Timeline([
    Event(timestamp_minutes=0, event_type="ingestion", payload={
        "compound_id": "caffeine",
        "amount": 100,
        "unit": "mg",
        "form": "liquid"
    })
])
person = VirtualPerson.create_reference()  # Normal CYP1A2
```

**Expected Output:**
```python
# Caffeine curve
assert 1.5 <= peak_caffeine <= 2.5  # mg/L for 100mg dose
assert 30 <= time_to_peak <= 60      # minutes
assert 4.0 <= half_life <= 6.0       # hours (normal metabolizer)

# Alertness
assert 60 <= peak_alertness <= 80    # % at peak
assert alertness_at_480min < 30      # Wearing off after 8h
```

**Source:** Blanchard 1983, typical 100mg caffeine PK

---

## SCENARIO 3: Mixed Meal - Breakfast
**Archivo:** `tests/golden/test_gs03_breakfast.py`

**Input:**
```python
timeline = Timeline([
    Event(timestamp_minutes=0, event_type="meal", payload={
        "carbs_g": 60,      # Oatmeal + banana
        "protein_g": 15,    # Eggs
        "fat_g": 12,        # Eggs + butter
        "fiber_g": 8,       # Oatmeal
        "glycemic_index": 55  # Mixed meal, lower GI
    })
])
```

**Expected Output:**
```python
# Glucose should be LOWER and SLOWER than OGTT due to fat/protein/fiber
assert 100 <= peak_glucose <= 140    # Lower than pure glucose
assert 45 <= time_to_peak <= 90      # Slower absorption
assert glucose_at_240min < 120       # Good return to baseline
```

**Source:** Meal effect literature, fiber/fat slowing absorption

---

## SCENARIO 4: Pre-Workout Stack
**Archivo:** `tests/golden/test_gs04_preworkout.py`

**Input:**
```python
timeline = Timeline([
    Event(timestamp_minutes=0, event_type="ingestion", payload={
        "compound_id": "caffeine", "amount": 200, "unit": "mg"
    }),
    Event(timestamp_minutes=0, event_type="ingestion", payload={
        "compound_id": "l_theanine", "amount": 100, "unit": "mg"
    }),
    Event(timestamp_minutes=0, event_type="meal", payload={
        "carbs_g": 30, "glycemic_index": 85
    })
])
```

**Expected Output:**
```python
# Caffeine+Theanine should reduce jitter
assert jitter_risk < 0.15  # <15% with theanine (vs ~30% without)

# Energy should be present
assert peak_alertness > 70

# Glucose response
assert 110 <= peak_glucose <= 150
```

**Source:** Caffeine+Theanine synergy literature

---

## SCENARIO 5: Day-Long Protocol (24h)
**Archivo:** `tests/golden/test_gs05_full_day.py`

**Input:**
```python
timeline = Timeline([
    # Morning coffee
    Event(timestamp_minutes=420, event_type="ingestion", payload={  # 7:00 AM
        "compound_id": "caffeine", "amount": 100, "unit": "mg"
    }),
    # Breakfast
    Event(timestamp_minutes=450, event_type="meal", payload={  # 7:30 AM
        "carbs_g": 50, "protein_g": 20, "fat_g": 15, "glycemic_index": 60
    }),
    # Lunch
    Event(timestamp_minutes=780, event_type="meal", payload={  # 13:00
        "carbs_g": 60, "protein_g": 30, "fat_g": 20, "glycemic_index": 55
    }),
    # Afternoon coffee
    Event(timestamp_minutes=900, event_type="ingestion", payload={  # 15:00
        "compound_id": "caffeine", "amount": 100, "unit": "mg"
    }),
    # Dinner
    Event(timestamp_minutes=1140, event_type="meal", payload={  # 19:00
        "carbs_g": 70, "protein_g": 25, "fat_g": 25, "glycemic_index": 50
    }),
])
```

**Expected Output:**
```python
# Multiple glucose peaks (one per meal)
assert len(glucose_peaks) == 3

# Caffeine accumulates
assert caffeine_at_1320 > 0.5  # Still present at 22:00 (10 PM)

# Sleep risk from afternoon coffee
assert sleep_disruption_risk > 0.2  # >20% risk

# State is continuous (no resets)
assert is_monotonic(timestamps)
assert no_discontinuities(glucose_curve)
```

**Source:** Real-world protocol validation

---

## SCENARIO 6: Slow vs Fast Caffeine Metabolizer
**Archivo:** `tests/golden/test_gs06_cyp1a2.py`

**Input:**
```python
timeline = Timeline([
    Event(timestamp_minutes=0, event_type="ingestion", payload={
        "compound_id": "caffeine", "amount": 200, "unit": "mg"
    })
])

person_slow = VirtualPerson(cyp1a2_genotype="slow", ...)
person_fast = VirtualPerson(cyp1a2_genotype="fast", ...)
```

**Expected Output:**
```python
# Half-life differs significantly
assert 6.5 <= slow_half_life <= 10.0  # hours
assert 2.5 <= fast_half_life <= 4.5   # hours

# Slow metabolizer has more caffeine at 8h
assert caffeine_slow_at_480 > 2 * caffeine_fast_at_480

# Sleep risk much higher for slow
assert sleep_risk_slow > sleep_risk_fast + 0.3
```

**Source:** CYP1A2 polymorphism literature

---

## SCENARIO 7: Insulin Resistant vs Sensitive
**Archivo:** `tests/golden/test_gs07_insulin_sensitivity.py`

**Input:**
```python
timeline = Timeline([
    Event(timestamp_minutes=0, event_type="meal", payload={
        "carbs_g": 50, "glycemic_index": 70
    })
])

person_sensitive = VirtualPerson(insulin_sensitivity_factor=1.5, ...)  # Athlete
person_resistant = VirtualPerson(insulin_sensitivity_factor=0.5, ...)  # Pre-diabetic
```

**Expected Output:**
```python
# Resistant has higher peak
assert peak_resistant > peak_sensitive + 20  # mg/dL

# Resistant takes longer to clear
assert time_to_baseline_resistant > time_to_baseline_sensitive + 30  # minutes

# Risk flags
assert hyperglycemia_risk_resistant > hyperglycemia_risk_sensitive
```

**Source:** Dalla Man parameter sensitivity, clinical data

---

## SCENARIO 8: Fasted vs Fed State
**Archivo:** `tests/golden/test_gs08_fasted_fed.py`

**Input:**
```python
# Scenario A: Caffeine fasted
timeline_fasted = Timeline([
    Event(timestamp_minutes=0, event_type="ingestion", payload={
        "compound_id": "caffeine", "amount": 200, "unit": "mg"
    })
])

# Scenario B: Caffeine with food
timeline_fed = Timeline([
    Event(timestamp_minutes=0, event_type="meal", payload={
        "carbs_g": 40, "fat_g": 15
    }),
    Event(timestamp_minutes=0, event_type="ingestion", payload={
        "compound_id": "caffeine", "amount": 200, "unit": "mg"
    })
])
```

**Expected Output:**
```python
# Fed state delays absorption
assert time_to_peak_fed > time_to_peak_fasted + 15  # minutes

# Peak may be slightly lower with food
assert peak_fed <= peak_fasted * 1.1

# Total AUC similar (bioavailability not affected)
assert abs(auc_fed - auc_fasted) / auc_fasted < 0.15
```

**Source:** Food-drug interaction literature

---

## SCENARIO 9: Population Distribution
**Archivo:** `tests/golden/test_gs09_population.py`

**Input:**
```python
timeline = Timeline([
    Event(timestamp_minutes=0, event_type="meal", payload={
        "carbs_g": 50, "glycemic_index": 70
    }),
    Event(timestamp_minutes=0, event_type="ingestion", payload={
        "compound_id": "caffeine", "amount": 150, "unit": "mg"
    })
])

population = PopulationGenerator().generate(n=1000, seed=42)
```

**Expected Output:**
```python
# Distribution sanity checks
assert 0.95 <= valid_simulations / 1000 <= 1.0  # >95% valid

# Glucose distribution
assert 100 <= glucose_p10 <= 130
assert 115 <= glucose_p50 <= 145
assert 140 <= glucose_p90 <= 180

# Caffeine distribution (CYP1A2 creates spread)
assert 2.0 <= caffeine_p50 <= 3.5
assert caffeine_p90 / caffeine_p10 > 1.5  # Meaningful spread

# Subgroup differences
assert hyperglycemia_rate_obese > hyperglycemia_rate_normal
assert sleep_risk_slow_metabolizers > sleep_risk_fast_metabolizers
```

**Source:** Population variability expectations

---

## SCENARIO 10: Reproducibility
**Archivo:** `tests/golden/test_gs10_reproducibility.py`

**Input:**
```python
timeline = [... any complex timeline ...]
config = SimulationConfig(seed=12345)
```

**Expected Output:**
```python
# Run twice with same seed
results_1 = simulate(timeline, config)
results_2 = simulate(timeline, config)

# EXACT match (not approximate)
assert results_1.glucose_curve == results_2.glucose_curve  # Exact
assert results_1.caffeine_curve == results_2.caffeine_curve  # Exact
assert results_1.metrics == results_2.metrics  # Exact

# Different seed = different results
config_2 = SimulationConfig(seed=99999)
results_3 = simulate(timeline, config_2)
assert results_3.metrics != results_1.metrics
```

**Source:** Determinism requirement for reproducibility

---

## RUNNING GOLDEN SCENARIOS

```bash
# Run all golden scenarios
pytest tests/golden/ -v

# Run specific scenario
pytest tests/golden/test_gs05_full_day.py -v

# Run with coverage
pytest tests/golden/ --cov=src/core -v
```

## ADDING NEW SCENARIOS

When adding a new golden scenario:
1. Create `tests/golden/test_gsXX_name.py`
2. Document input, expected output, and source
3. Add to this file
4. Scenarios should NEVER be deleted, only deprecated with reason

## TOLERANCES

Most golden scenarios use RANGES not exact values because:
- Biological variability is real
- Model parameters have uncertainty
- We want to catch BROKEN behavior, not SLIGHTLY DIFFERENT behavior

If a scenario fails by a small margin, investigate before changing tolerances.
