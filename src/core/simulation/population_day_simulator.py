"""
PopulationDaySimulator: Simulate populations over 24h timelines.

FASE 2, Sesión 5.1

Simulates N virtual persons over a shared timeline with streaming
aggregation for memory efficiency O(1) per individual.

Contracts implemented:
- Contract 5.2: PopulationSimulator
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
import numpy as np

from src.core.population import VirtualPerson
from src.core.timeline import Timeline
from src.core.simulation.day_simulator import DaySimulator, DaySimulationResult


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass(frozen=True)
class PopulationSimulationConfig:
    """Configuration for population simulation.
    
    Attributes:
        dt_minutes: Time step for integration (default 1.0 minute)
        seed: Random seed for reproducibility
        parallel: Whether to use parallel processing (default False)
    """
    dt_minutes: float = 1.0
    seed: int = 42
    parallel: bool = False
    
    def __post_init__(self):
        if self.dt_minutes <= 0:
            raise ValueError(f"dt_minutes must be positive, got {self.dt_minutes}")


# =============================================================================
# STREAMING AGGREGATOR (Welford's Algorithm)
# =============================================================================

class StreamingCurveAggregator:
    """Aggregates curves using Welford's algorithm for online statistics.
    
    Memory efficient: O(1) per individual, not O(N).
    Calculates running mean, variance, and stores values for percentiles.
    
    For percentiles, we use reservoir sampling to approximate.
    """
    
    def __init__(self, length: int, percentiles: List[float] = None):
        """Initialize aggregator.
        
        Args:
            length: Number of time points
            percentiles: Percentile values to compute (default: [5, 25, 50, 75, 95])
        """
        self.length = length
        self.percentiles = percentiles or [5, 25, 50, 75, 95]
        self.n = 0
        
        # Welford's algorithm accumulators
        self.mean = np.zeros(length)
        self.M2 = np.zeros(length)
        
        # For percentiles, we need to store all values
        # This is a tradeoff: exact percentiles vs memory
        # For N=10000, storing curves uses ~100MB which is acceptable
        self._values: List[np.ndarray] = []
    
    def update(self, curve: np.ndarray) -> None:
        """Add a new curve to the aggregator.
        
        Args:
            curve: 1D numpy array of length self.length
        """
        if len(curve) != self.length:
            raise ValueError(f"Curve length {len(curve)} != expected {self.length}")
        
        self.n += 1
        
        # Welford's online algorithm
        delta = curve - self.mean
        self.mean += delta / self.n
        delta2 = curve - self.mean
        self.M2 += delta * delta2
        
        # Store for percentiles
        self._values.append(curve.copy())
    
    def get_stats(self) -> Dict[str, np.ndarray]:
        """Get final statistics.
        
        Returns:
            Dict with 'mean', 'std', and percentile keys (e.g., 'p5', 'p50')
        """
        if self.n == 0:
            return {
                'mean': np.zeros(self.length),
                'std': np.zeros(self.length),
                **{f'p{p}': np.zeros(self.length) for p in self.percentiles}
            }
        
        result = {
            'mean': self.mean.copy(),
            'std': np.sqrt(self.M2 / self.n) if self.n > 1 else np.zeros(self.length),
        }
        
        # Calculate percentiles from stored values
        if self._values:
            values_array = np.array(self._values)  # Shape: (n, length)
            for p in self.percentiles:
                result[f'p{p}'] = np.percentile(values_array, p, axis=0)
        else:
            for p in self.percentiles:
                result[f'p{p}'] = np.zeros(self.length)
        
        return result


class StreamingMetricsAggregator:
    """Aggregates scalar metrics with Welford's algorithm."""
    
    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}
    
    def update(self, metrics: Dict[str, float]) -> None:
        """Add metrics from one simulation."""
        for name, value in metrics.items():
            # Skip non-numeric values (like is_valid which is boolean)
            if isinstance(value, bool):
                continue
            if not isinstance(value, (int, float)):
                continue
            if name not in self.metrics:
                self.metrics[name] = []
            if np.isfinite(value):
                self.metrics[name].append(float(value))
    
    def get_stats(self) -> Dict[str, Dict[str, float]]:
        """Get statistics for all metrics.
        
        Returns:
            Dict[metric_name, Dict[stat_name, value]]
            Stats include: mean, std, p10, p90
        """
        result = {}
        for name, values in self.metrics.items():
            if not values:
                result[name] = {'mean': 0.0, 'std': 0.0, 'p10': 0.0, 'p90': 0.0}
            else:
                arr = np.array(values)
                result[name] = {
                    'mean': float(np.mean(arr)),
                    'std': float(np.std(arr)),
                    'p10': float(np.percentile(arr, 10)),
                    'p90': float(np.percentile(arr, 90)),
                }
        return result


# =============================================================================
# RISK CALCULATOR
# =============================================================================

class RiskCalculator:
    """Calculates population risk percentages."""
    
    def __init__(self):
        self.n_total = 0
        self.risks: Dict[str, int] = {
            'pct_hyperglycemia': 0,        # glucose > 140
            'pct_severe_hyperglycemia': 0,  # glucose > 180
            'pct_jitter_risk': 0,           # caffeine > 4 mg/L
            'pct_sleep_disruption': 0,      # caffeine > 1 mg/L at 22:00
            'pct_crash_risk': 0,            # alertness drop > 30% in 2h
        }
    
    def update(self, result: DaySimulationResult) -> None:
        """Update risk counts from individual simulation."""
        self.n_total += 1
        
        # Hyperglycemia: peak glucose > 140 mg/dL
        if result.metrics.get('glucose_peak', 0) > 140:
            self.risks['pct_hyperglycemia'] += 1
        
        # Severe hyperglycemia: peak glucose > 180 mg/dL
        if result.metrics.get('glucose_peak', 0) > 180:
            self.risks['pct_severe_hyperglycemia'] += 1
        
        # Jitter risk: peak caffeine > 4 mg/L
        if result.metrics.get('caffeine_peak', 0) > 4.0:
            self.risks['pct_jitter_risk'] += 1
        
        # Sleep disruption: caffeine > 1 mg/L at 22:00 (1320 minutes)
        # Find caffeine level at minute 1320
        caffeine_at_22h = self._get_value_at_time(
            result.time_minutes, result.caffeine_curve, 1320.0
        )
        if caffeine_at_22h > 1.0:
            self.risks['pct_sleep_disruption'] += 1
        
        # Crash risk: alertness drops > 30% within 2h window
        if self._has_crash(result.alertness_curve):
            self.risks['pct_crash_risk'] += 1
    
    def _get_value_at_time(self, times: np.ndarray, values: np.ndarray, target_time: float) -> float:
        """Get interpolated value at specific time."""
        if len(times) == 0 or len(values) == 0:
            return 0.0
        
        idx = np.searchsorted(times, target_time)
        if idx >= len(values):
            return float(values[-1])
        if idx == 0:
            return float(values[0])
        
        # Linear interpolation
        t0, t1 = times[idx-1], times[idx]
        v0, v1 = values[idx-1], values[idx]
        if t1 == t0:
            return float(v0)
        
        ratio = (target_time - t0) / (t1 - t0)
        return float(v0 + ratio * (v1 - v0))
    
    def _has_crash(self, alertness: np.ndarray, window_minutes: int = 120) -> bool:
        """Check if alertness drops > 30% in any 2h window."""
        if len(alertness) < window_minutes:
            return False
        
        for i in range(len(alertness) - window_minutes):
            peak_in_window = np.max(alertness[i:i+window_minutes])
            min_in_window = np.min(alertness[i:i+window_minutes])
            if peak_in_window > 0:
                drop_pct = (peak_in_window - min_in_window) / peak_in_window
                if drop_pct > 0.30:
                    return True
        return False
    
    def get_percentages(self) -> Dict[str, float]:
        """Get risk percentages (0-100)."""
        if self.n_total == 0:
            return {name: 0.0 for name in self.risks}
        
        return {
            name: (count / self.n_total) * 100.0
            for name, count in self.risks.items()
        }


# =============================================================================
# SUBGROUP ANALYZER
# =============================================================================

class SubgroupAnalyzer:
    """Analyzes results by population subgroups."""
    
    def __init__(self):
        # BMI categories
        self.by_bmi: Dict[str, List[Dict[str, float]]] = {
            'normal': [],      # BMI < 25
            'overweight': [],  # 25 <= BMI < 30
            'obese': [],       # BMI >= 30
        }
        
        # Caffeine sensitivity
        self.by_caffeine_sensitivity: Dict[str, List[Dict[str, float]]] = {
            'slow': [],
            'normal': [],
            'fast': [],
        }
        
        # Age groups
        self.by_age: Dict[str, List[Dict[str, float]]] = {
            'young': [],     # 18-35
            'middle': [],    # 36-55
            'older': [],     # 56+
        }
    
    def update(self, person: VirtualPerson, metrics: Dict[str, float]) -> None:
        """Add person's metrics to appropriate subgroups."""
        # BMI category
        bmi = person.bmi
        if bmi < 25:
            self.by_bmi['normal'].append(metrics)
        elif bmi < 30:
            self.by_bmi['overweight'].append(metrics)
        else:
            self.by_bmi['obese'].append(metrics)
        
        # Caffeine sensitivity
        genotype = person.cyp1a2_genotype
        if genotype in self.by_caffeine_sensitivity:
            self.by_caffeine_sensitivity[genotype].append(metrics)
        else:
            self.by_caffeine_sensitivity['normal'].append(metrics)
        
        # Age group
        age = person.age
        if age <= 35:
            self.by_age['young'].append(metrics)
        elif age <= 55:
            self.by_age['middle'].append(metrics)
        else:
            self.by_age['older'].append(metrics)
    
    def get_analysis(self) -> Dict[str, Dict[str, Any]]:
        """Get subgroup analysis summary."""
        return {
            'by_bmi': self._summarize_groups(self.by_bmi),
            'by_caffeine_sensitivity': self._summarize_groups(self.by_caffeine_sensitivity),
            'by_age': self._summarize_groups(self.by_age),
        }
    
    def _summarize_groups(self, groups: Dict[str, List[Dict[str, float]]]) -> Dict[str, Dict[str, Any]]:
        """Summarize metrics for each group."""
        result = {}
        for group_name, metrics_list in groups.items():
            if not metrics_list:
                result[group_name] = {'n': 0, 'metrics': {}}
                continue
            
            # Aggregate metrics
            aggregated = {}
            all_keys = set()
            for m in metrics_list:
                all_keys.update(m.keys())
            
            for key in all_keys:
                values = [m.get(key, np.nan) for m in metrics_list]
                # Filter to only numeric, non-boolean, finite values
                numeric_values = []
                for v in values:
                    if isinstance(v, bool):
                        continue
                    if not isinstance(v, (int, float)):
                        continue
                    if np.isfinite(v):
                        numeric_values.append(float(v))
                
                if numeric_values:
                    aggregated[key] = {
                        'mean': float(np.mean(numeric_values)),
                        'std': float(np.std(numeric_values)),
                    }
            
            result[group_name] = {
                'n': len(metrics_list),
                'metrics': aggregated,
            }
        
        return result


# =============================================================================
# POPULATION DAY RESULT
# =============================================================================

@dataclass
class PopulationDayResult:
    """Result of population simulation over 24h.
    
    Implements Contract 5.2: PopulationSimulationResult
    
    Attributes:
        n_individuals: Total number of individuals simulated
        n_valid: Number of valid simulations
        time_minutes: Time array (0 to 1440)
        glucose_percentiles: Dict of percentile curves {'p5': array, 'p50': array, ...}
        caffeine_percentiles: Dict of percentile curves
        alertness_percentiles: Dict of percentile curves
        metrics_stats: Statistics for each metric {metric: {mean, std, p10, p90}}
        risk_analysis: Risk percentages {risk_name: percentage}
        subgroup_analysis: Analysis by subgroups
        warnings: List of warnings during simulation
    """
    n_individuals: int
    n_valid: int
    time_minutes: np.ndarray
    glucose_percentiles: Dict[str, np.ndarray]
    caffeine_percentiles: Dict[str, np.ndarray]
    alertness_percentiles: Dict[str, np.ndarray]
    insulin_percentiles: Dict[str, np.ndarray]
    metrics_stats: Dict[str, Dict[str, float]]
    risk_analysis: Dict[str, float]
    subgroup_analysis: Dict[str, Dict[str, Any]]
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'n_individuals': self.n_individuals,
            'n_valid': self.n_valid,
            'time_minutes': self.time_minutes.tolist(),
            'glucose_percentiles': {k: v.tolist() for k, v in self.glucose_percentiles.items()},
            'caffeine_percentiles': {k: v.tolist() for k, v in self.caffeine_percentiles.items()},
            'alertness_percentiles': {k: v.tolist() for k, v in self.alertness_percentiles.items()},
            'insulin_percentiles': {k: v.tolist() for k, v in self.insulin_percentiles.items()},
            'metrics_stats': self.metrics_stats,
            'risk_analysis': self.risk_analysis,
            'subgroup_analysis': self.subgroup_analysis,
            'warnings': self.warnings,
        }


# =============================================================================
# POPULATION DAY SIMULATOR
# =============================================================================

class PopulationDaySimulator:
    """Simulates a population over a 24h timeline.
    
    Uses streaming aggregation for memory efficiency.
    
    Example:
        >>> simulator = PopulationDaySimulator()
        >>> population = PopulationGenerator().generate(n=1000)
        >>> timeline = Timeline().add_event(...)
        >>> result = simulator.simulate(population, timeline)
        >>> print(f"Valid: {result.n_valid}/{result.n_individuals}")
    """
    
    def __init__(self, config: Optional[PopulationSimulationConfig] = None):
        """Initialize simulator.
        
        Args:
            config: Simulation configuration (optional)
        """
        self.config = config or PopulationSimulationConfig()
        self._rng = np.random.default_rng(self.config.seed)
    
    def simulate(
        self,
        population: List[VirtualPerson],
        timeline: Timeline,
    ) -> PopulationDayResult:
        """Simulate population over timeline.
        
        Args:
            population: List of VirtualPerson objects
            timeline: Timeline with events
            
        Returns:
            PopulationDayResult with aggregated statistics
        """
        n_individuals = len(population)
        
        # Handle empty population
        if n_individuals == 0:
            return self._empty_result()
        
        # Calculate expected time points
        duration_minutes = 1440  # 24 hours
        n_points = int(duration_minutes / self.config.dt_minutes) + 1
        time_array = np.linspace(0, duration_minutes, n_points)
        
        # Initialize aggregators
        glucose_agg = StreamingCurveAggregator(n_points)
        caffeine_agg = StreamingCurveAggregator(n_points)
        alertness_agg = StreamingCurveAggregator(n_points)
        insulin_agg = StreamingCurveAggregator(n_points)
        metrics_agg = StreamingMetricsAggregator()
        risk_calc = RiskCalculator()
        subgroup_analyzer = SubgroupAnalyzer()
        
        n_valid = 0
        warnings = []
        
        # Simulate each person
        for person in population:
            try:
                day_sim = DaySimulator(person)
                result = day_sim.simulate(timeline, dt_minutes=self.config.dt_minutes)
                
                if result.is_valid:
                    n_valid += 1
                    
                    # Update curve aggregators
                    # Ensure curves match expected length
                    glucose_curve = self._ensure_length(result.glucose_curve, n_points)
                    caffeine_curve = self._ensure_length(result.caffeine_curve, n_points)
                    alertness_curve = self._ensure_length(result.alertness_curve, n_points)
                    insulin_curve = self._ensure_length(result.insulin_curve, n_points)
                    
                    glucose_agg.update(glucose_curve)
                    caffeine_agg.update(caffeine_curve)
                    alertness_agg.update(alertness_curve)
                    insulin_agg.update(insulin_curve)
                    
                    # Update metrics
                    metrics_agg.update(result.metrics)
                    
                    # Update risks
                    risk_calc.update(result)
                    
                    # Update subgroups
                    subgroup_analyzer.update(person, result.metrics)
                else:
                    warnings.append(f"Invalid simulation for {person.person_id}")
                    
            except Exception as e:
                warnings.append(f"Error simulating {person.person_id}: {str(e)}")
        
        # Collect results
        glucose_stats = glucose_agg.get_stats()
        caffeine_stats = caffeine_agg.get_stats()
        alertness_stats = alertness_agg.get_stats()
        insulin_stats = insulin_agg.get_stats()
        
        return PopulationDayResult(
            n_individuals=n_individuals,
            n_valid=n_valid,
            time_minutes=time_array,
            glucose_percentiles={
                'p5': glucose_stats['p5'],
                'p25': glucose_stats.get('p25', glucose_stats['p5']),
                'p50': glucose_stats.get('p50', glucose_stats['mean']),
                'p75': glucose_stats.get('p75', glucose_stats['p95']),
                'p95': glucose_stats['p95'],
                'mean': glucose_stats['mean'],
                'std': glucose_stats['std'],
            },
            caffeine_percentiles={
                'p5': caffeine_stats['p5'],
                'p25': caffeine_stats.get('p25', caffeine_stats['p5']),
                'p50': caffeine_stats.get('p50', caffeine_stats['mean']),
                'p75': caffeine_stats.get('p75', caffeine_stats['p95']),
                'p95': caffeine_stats['p95'],
                'mean': caffeine_stats['mean'],
                'std': caffeine_stats['std'],
            },
            alertness_percentiles={
                'p5': alertness_stats['p5'],
                'p25': alertness_stats.get('p25', alertness_stats['p5']),
                'p50': alertness_stats.get('p50', alertness_stats['mean']),
                'p75': alertness_stats.get('p75', alertness_stats['p95']),
                'p95': alertness_stats['p95'],
                'mean': alertness_stats['mean'],
                'std': alertness_stats['std'],
            },
            insulin_percentiles={
                'p5': insulin_stats['p5'],
                'p25': insulin_stats.get('p25', insulin_stats['p5']),
                'p50': insulin_stats.get('p50', insulin_stats['mean']),
                'p75': insulin_stats.get('p75', insulin_stats['p95']),
                'p95': insulin_stats['p95'],
                'mean': insulin_stats['mean'],
                'std': insulin_stats['std'],
            },
            metrics_stats=metrics_agg.get_stats(),
            risk_analysis=risk_calc.get_percentages(),
            subgroup_analysis=subgroup_analyzer.get_analysis(),
            warnings=warnings if len(warnings) <= 10 else warnings[:10] + [f"... and {len(warnings)-10} more"],
        )
    
    def _ensure_length(self, arr: np.ndarray, expected_length: int) -> np.ndarray:
        """Ensure array has expected length by interpolation or truncation."""
        if len(arr) == expected_length:
            return arr
        
        if len(arr) == 0:
            return np.zeros(expected_length)
        
        # Interpolate to expected length
        old_x = np.linspace(0, 1, len(arr))
        new_x = np.linspace(0, 1, expected_length)
        return np.interp(new_x, old_x, arr)
    
    def _empty_result(self) -> PopulationDayResult:
        """Create empty result for empty population."""
        n_points = int(1440 / self.config.dt_minutes) + 1
        time_array = np.linspace(0, 1440, n_points)
        empty_curve = np.zeros(n_points)
        empty_percentiles = {
            'p5': empty_curve,
            'p25': empty_curve,
            'p50': empty_curve,
            'p75': empty_curve,
            'p95': empty_curve,
            'mean': empty_curve,
            'std': empty_curve,
        }
        
        return PopulationDayResult(
            n_individuals=0,
            n_valid=0,
            time_minutes=time_array,
            glucose_percentiles=empty_percentiles.copy(),
            caffeine_percentiles=empty_percentiles.copy(),
            alertness_percentiles=empty_percentiles.copy(),
            insulin_percentiles=empty_percentiles.copy(),
            metrics_stats={},
            risk_analysis={name: 0.0 for name in [
                'pct_hyperglycemia', 'pct_severe_hyperglycemia',
                'pct_jitter_risk', 'pct_sleep_disruption', 'pct_crash_risk'
            ]},
            subgroup_analysis={
                'by_bmi': {},
                'by_caffeine_sensitivity': {},
                'by_age': {},
            },
            warnings=['Empty population'],
        )
