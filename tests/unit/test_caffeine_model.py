import pytest
import numpy as np
from src.core.models.caffeine import EliteCaffeineModel, EliteCaffeineInput

@pytest.fixture
def model():
    return EliteCaffeineModel()

def test_basic_pk_shape(model):
    """Verifica que la curva de sangre tenga forma lógica (sube y baja)"""
    inputs = EliteCaffeineInput(dose_mg=200, body_weight_kg=75, tolerance_days=0, sleep_debt_hours=0)
    result = model.simulate(inputs)
    
    # Debe haber un pico
    assert result.metrics["Cmax"] > 0
    # Tmax debe estar entre 30 y 90 min (considerando lag de 15 min + absorción)
    assert 30 <= result.metrics["Tmax"] <= 90
    # Al final (8h) la concentración debe ser menor que el pico
    assert result.plasma_concentration[-1] < result.metrics["Cmax"]

def test_tolerance_effect(model):
    """
    CRÍTICO: Un usuario con tolerancia (30 días de uso) debe tener 
    MENOS ocupación de receptores que un usuario nuevo con la misma dosis.
    """
    naive_in = EliteCaffeineInput(200, 75, tolerance_days=0, sleep_debt_hours=0)
    habitual_in = EliteCaffeineInput(200, 75, tolerance_days=30, sleep_debt_hours=0)
    
    res_naive = model.simulate(naive_in)
    res_habitual = model.simulate(habitual_in)
    
    # La concentración en sangre es idéntica (PK no cambia por tolerancia PD)
    assert np.isclose(res_naive.metrics["Cmax"], res_habitual.metrics["Cmax"], atol=0.1)
    
    # PERO la ocupación de receptores debe ser menor en el usuario habitual
    assert res_habitual.metrics["Peak_Occupancy_Pct"] < res_naive.metrics["Peak_Occupancy_Pct"]
    print(f"\nNaive Occupancy: {res_naive.metrics['Peak_Occupancy_Pct']}%")
    print(f"Habitual Occupancy: {res_habitual.metrics['Peak_Occupancy_Pct']}%")

def test_sleep_debt_impact(model):
    """
    Verifica que la deuda de sueño reduce la alerta neta máxima alcanzable.
    """
    rested_in = EliteCaffeineInput(200, 75, 0, sleep_debt_hours=0)
    tired_in = EliteCaffeineInput(200, 75, 0, sleep_debt_hours=4) # 4 horas de deuda
    
    res_rested = model.simulate(rested_in)
    res_tired = model.simulate(tired_in)
    
    # El usuario cansado debe tener menor alerta máxima
    assert np.max(res_tired.net_alertness) < np.max(res_rested.net_alertness)

def test_crash_detection(model):
    """
    Simula una dosis alta con caída rápida para ver si detecta el crash.
    """
    # Dosis media en persona pequeña con metabolismo rápido (simulado implícitamente por params)
    inputs = EliteCaffeineInput(dose_mg=300, body_weight_kg=60, tolerance_days=0, sleep_debt_hours=2)
    result = model.simulate(inputs)
    
    # Verificamos que los arrays tengan datos
    assert len(result.net_alertness) > 0
    # Verificamos que crash_detected sea booleano
    assert isinstance(result.crash_detected, bool)