#!/usr/bin/env python3
"""
MODULUS Demo - Simulación desde Terminal
=========================================

Ejecuta una simulación completa y muestra los resultados.

Uso:
    python demo_simulation.py

O con parámetros personalizados:
    python demo_simulation.py --carbs 50 --caffeine 200 --population 500
"""

import sys
import argparse
import json
from datetime import datetime

# Añadir src al path
sys.path.insert(0, 'src')

def run_demo(carbs: float, gi: float, caffeine: float, protein: float, 
             fat: float, fiber: float, population: int, seed: int,
             subpopulation: str = None):
    """Ejecuta simulación y muestra resultados."""
    
    print("=" * 70)
    print("🧬 MODULUS — In-Silico Metabolic Response Simulator")
    print("=" * 70)
    
    # Importar después de añadir path
    from core import SimulationEngine, SimulationConfig, ProductComposition
    
    # Crear producto
    product = ProductComposition(
        name="Demo Product",
        carbohydrates_g=carbs,
        glycemic_index=gi,
        caffeine_mg=caffeine,
        protein_g=protein,
        fat_g=fat,
        fiber_g=fiber,
    )
    
    # Mostrar inputs
    print("\n📦 PRODUCTO:")
    print(f"   Carbohidratos: {carbs}g (GI: {gi})")
    print(f"   Proteína: {protein}g")
    print(f"   Grasa: {fat}g")
    print(f"   Fibra: {fiber}g")
    print(f"   Cafeína: {caffeine}mg")
    
    # Configuración
    config = SimulationConfig(
        population_size=population,
        population_seed=seed,
        duration_minutes=240,
        subpopulation=subpopulation,
        store_timeseries=False,  # Modo producción
        store_individual_results=False,
    )
    
    print(f"\n👥 POBLACIÓN:")
    print(f"   Tamaño: {population} individuos virtuales")
    print(f"   Seed: {seed} (reproducible)")
    if subpopulation:
        print(f"   Subpoblación: {subpopulation}")
    
    # Ejecutar
    print(f"\n⚡ Ejecutando simulación...")
    print("-" * 70)
    
    engine = SimulationEngine()
    results = engine.run(product, config)
    
    # Mostrar resultados
    print("\n" + "=" * 70)
    print("📊 RESULTADOS")
    print("=" * 70)
    
    print(f"\n✅ Simulaciones válidas: {results.n_valid}/{results.n_individuals} ({results.n_valid/results.n_individuals*100:.1f}%)")
    print(f"⏱️  Tiempo: {results.duration_seconds:.2f}s")
    
    # Glucosa
    if results.glucose_stats.get('peak'):
        g = results.glucose_stats
        print(f"\n🩸 GLUCOSA:")
        print(f"   Peak:        {g['peak']['mean']:.1f} ± {g['peak']['std']:.1f} mg/dL")
        print(f"   Rango:       [{g['peak']['min']:.1f} - {g['peak']['max']:.1f}] mg/dL")
        print(f"   Percentiles: p10={g['peak'].get('p10', 0):.1f}, p50={g['peak'].get('p50', 0):.1f}, p90={g['peak'].get('p90', 0):.1f}")
        if g.get('time_to_peak'):
            print(f"   Time to peak: {g['time_to_peak']['mean']:.0f} min")
    
    # Cafeína
    if results.caffeine_stats.get('peak') and results.caffeine_stats['peak'].get('mean', 0) > 0:
        c = results.caffeine_stats
        print(f"\n☕ CAFEÍNA:")
        print(f"   Peak:        {c['peak']['mean']:.2f} ± {c['peak']['std']:.2f} mg/L")
        print(f"   Rango:       [{c['peak']['min']:.2f} - {c['peak']['max']:.2f}] mg/L")
        if c.get('alertness_peak'):
            print(f"   Alertness:   {c['alertness_peak']['mean']:.1f}% (pico)")
    
    # Riesgos
    r = results.risk_analysis
    print(f"\n⚠️  ANÁLISIS DE RIESGO:")
    print(f"   Hiperglucemia (>140):     {r.get('pct_hyperglycemia', 0):.1f}% de la población")
    print(f"   Hiperglucemia severa:     {r.get('pct_severe_hyperglycemia', 0):.1f}%")
    print(f"   Hipoglucemia (<70):       {r.get('pct_hypoglycemia', 0):.1f}%")
    print(f"   Crash energético:         {r.get('pct_crash_risk', 0):.1f}%")
    if caffeine > 0:
        print(f"   Jitter (ansiedad):        {r.get('pct_jitter_risk', 0):.1f}%")
        print(f"   Disrupción sueño:         {r.get('pct_sleep_risk', 0):.1f}%")
    
    # Subgrupos
    if results.subgroup_analysis.get('by_bmi'):
        print(f"\n📈 ANÁLISIS POR SUBGRUPOS (BMI):")
        for bmi_cat, data in results.subgroup_analysis['by_bmi'].items():
            if data.get('n', 0) > 0:
                print(f"   {bmi_cat:12} (n={data['n']:3}): peak={data.get('avg_peak_glucose', 0):.1f} mg/dL, hyperglycemia={data.get('pct_hyperglycemia', 0):.1f}%")
    
    # Metadata
    print(f"\n🔍 METADATA (Auditoría):")
    print(f"   Engine:      {results.engine_version}")
    print(f"   Glucose:     {results.glucose_model_version}")
    print(f"   Caffeine:    {results.caffeine_model_version}")
    print(f"   Simulation:  {results.simulation_id}")
    
    print("\n" + "=" * 70)
    print("✅ Simulación completada")
    print("=" * 70)
    
    # Guardar JSON opcional
    save_json = input("\n¿Guardar resultados en JSON? (s/n): ").strip().lower()
    if save_json == 's':
        filename = f"simulation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(results.to_dict(), f, indent=2)
        print(f"💾 Guardado en: {filename}")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description="MODULUS - Simulador de Respuesta Metabólica",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python demo_simulation.py
  python demo_simulation.py --carbs 50 --caffeine 200
  python demo_simulation.py --carbs 30 --gi 85 --caffeine 150 --population 1000
  python demo_simulation.py --subpop athletes --population 500
        """
    )
    
    # Producto
    parser.add_argument('--carbs', type=float, default=30, help='Carbohidratos (g) [default: 30]')
    parser.add_argument('--gi', type=float, default=70, help='Índice glucémico [default: 70]')
    parser.add_argument('--caffeine', type=float, default=100, help='Cafeína (mg) [default: 100]')
    parser.add_argument('--protein', type=float, default=0, help='Proteína (g) [default: 0]')
    parser.add_argument('--fat', type=float, default=0, help='Grasa (g) [default: 0]')
    parser.add_argument('--fiber', type=float, default=0, help='Fibra (g) [default: 0]')
    
    # Simulación
    parser.add_argument('--population', '-n', type=int, default=200, help='Tamaño población [default: 200]')
    parser.add_argument('--seed', type=int, default=42, help='Seed para reproducibilidad [default: 42]')
    parser.add_argument('--subpop', type=str, default=None, 
                       choices=['athletes', 'prediabetic', 'elderly', 'young_adults', 'obese'],
                       help='Filtrar subpoblación')
    
    args = parser.parse_args()
    
    run_demo(
        carbs=args.carbs,
        gi=args.gi,
        caffeine=args.caffeine,
        protein=args.protein,
        fat=args.fat,
        fiber=args.fiber,
        population=args.population,
        seed=args.seed,
        subpopulation=args.subpop,
    )


if __name__ == "__main__":
    main()
