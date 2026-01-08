"""
Tests for Full Risk Map (6 segments) - Session 10.1
MODULUS - Decision & Compliance OS

Tests for:
- 3 new segmentation dimensions (insulin sensitivity, activity level, habitual caffeine)
- Risk matrix (segment × risk)
- Danger zone identification
- Population percentage per cell

UPDATED to match actual implementation API.
"""

import pytest
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import numpy as np


# =============================================================================
# TEST: Segment Definitions
# =============================================================================

class TestSegmentDefinitions:
    """Test that all 6 segment types are properly defined."""
    
    def test_bmi_segments_exist(self):
        """BMI segments: normal, overweight, obese."""
        from src.analysis.risk import SegmentationType
        assert hasattr(SegmentationType, 'BMI')
        
    def test_age_segments_exist(self):
        """Age segments: young, middle, older."""
        from src.analysis.risk import SegmentationType
        assert hasattr(SegmentationType, 'AGE')
        
    def test_caffeine_sensitivity_segments_exist(self):
        """Caffeine sensitivity segments: slow, normal, fast."""
        from src.analysis.risk import SegmentationType
        assert hasattr(SegmentationType, 'CAFFEINE_SENSITIVITY')
        
    def test_insulin_sensitivity_segments_exist(self):
        """Insulin sensitivity segments: sensitive, normal, resistant."""
        from src.analysis.risk import SegmentationType
        assert hasattr(SegmentationType, 'INSULIN_SENSITIVITY')
        
    def test_activity_level_segments_exist(self):
        """Activity level segments: sedentary, moderate, active."""
        from src.analysis.risk import SegmentationType
        assert hasattr(SegmentationType, 'ACTIVITY_LEVEL')
        
    def test_habitual_caffeine_segments_exist(self):
        """Habitual caffeine segments: naive, moderate, heavy."""
        from src.analysis.risk import SegmentationType
        assert hasattr(SegmentationType, 'HABITUAL_CAFFEINE')


class TestSegmentClassifier:
    """Test segment classification logic."""
    
    def test_classify_bmi_normal(self):
        """BMI < 25 is normal."""
        from src.analysis.risk import SegmentClassifier
        classifier = SegmentClassifier()
        assert classifier.classify_bmi(22.0) == "normal"
        assert classifier.classify_bmi(24.9) == "normal"
        
    def test_classify_bmi_overweight(self):
        """BMI 25-30 is overweight."""
        from src.analysis.risk import SegmentClassifier
        classifier = SegmentClassifier()
        assert classifier.classify_bmi(25.0) == "overweight"
        assert classifier.classify_bmi(29.9) == "overweight"
        
    def test_classify_bmi_obese(self):
        """BMI >= 30 is obese."""
        from src.analysis.risk import SegmentClassifier
        classifier = SegmentClassifier()
        assert classifier.classify_bmi(30.0) == "obese"
        assert classifier.classify_bmi(40.0) == "obese"
        
    def test_classify_age_young(self):
        """Age 18-35 is young."""
        from src.analysis.risk import SegmentClassifier
        classifier = SegmentClassifier()
        assert classifier.classify_age(18) == "young"
        assert classifier.classify_age(35) == "young"
        
    def test_classify_age_middle(self):
        """Age 36-55 is middle."""
        from src.analysis.risk import SegmentClassifier
        classifier = SegmentClassifier()
        assert classifier.classify_age(36) == "middle"
        assert classifier.classify_age(55) == "middle"
        
    def test_classify_age_older(self):
        """Age 56+ is older."""
        from src.analysis.risk import SegmentClassifier
        classifier = SegmentClassifier()
        assert classifier.classify_age(56) == "older"
        assert classifier.classify_age(80) == "older"
        
    def test_classify_caffeine_sensitivity_slow(self):
        """CYP1A2 slow genotype is slow."""
        from src.analysis.risk import SegmentClassifier
        classifier = SegmentClassifier()
        assert classifier.classify_caffeine_sensitivity("slow") == "slow"
        assert classifier.classify_caffeine_sensitivity("SLOW") == "slow"
        
    def test_classify_caffeine_sensitivity_normal(self):
        """CYP1A2 normal genotype is normal."""
        from src.analysis.risk import SegmentClassifier
        classifier = SegmentClassifier()
        assert classifier.classify_caffeine_sensitivity("normal") == "normal"
        
    def test_classify_caffeine_sensitivity_fast(self):
        """CYP1A2 fast genotype is fast."""
        from src.analysis.risk import SegmentClassifier
        classifier = SegmentClassifier()
        assert classifier.classify_caffeine_sensitivity("fast") == "fast"
        
    # NEW: Insulin sensitivity
    def test_classify_insulin_sensitivity_sensitive(self):
        """ISF > 1.2 is sensitive."""
        from src.analysis.risk import SegmentClassifier
        classifier = SegmentClassifier()
        assert classifier.classify_insulin_sensitivity(1.3) == "sensitive"
        assert classifier.classify_insulin_sensitivity(1.5) == "sensitive"
        
    def test_classify_insulin_sensitivity_normal(self):
        """ISF 0.8-1.2 is normal."""
        from src.analysis.risk import SegmentClassifier
        classifier = SegmentClassifier()
        assert classifier.classify_insulin_sensitivity(0.8) == "normal"
        assert classifier.classify_insulin_sensitivity(1.0) == "normal"
        assert classifier.classify_insulin_sensitivity(1.2) == "normal"
        
    def test_classify_insulin_sensitivity_resistant(self):
        """ISF < 0.8 is resistant."""
        from src.analysis.risk import SegmentClassifier
        classifier = SegmentClassifier()
        assert classifier.classify_insulin_sensitivity(0.5) == "resistant"
        assert classifier.classify_insulin_sensitivity(0.79) == "resistant"
        
    # NEW: Activity level (UPDATED to match implementation)
    def test_classify_activity_level_sedentary(self):
        """Activity sedentary is sedentary."""
        from src.analysis.risk import SegmentClassifier
        classifier = SegmentClassifier()
        assert classifier.classify_activity_level("sedentary") == "sedentary"
        # Note: "light" maps to "moderate" in the implementation
        
    def test_classify_activity_level_moderate(self):
        """Activity light or moderate is moderate."""
        from src.analysis.risk import SegmentClassifier
        classifier = SegmentClassifier()
        assert classifier.classify_activity_level("light") == "moderate"
        assert classifier.classify_activity_level("moderate") == "moderate"
        
    def test_classify_activity_level_active(self):
        """Activity active or very_active is active."""
        from src.analysis.risk import SegmentClassifier
        classifier = SegmentClassifier()
        assert classifier.classify_activity_level("active") == "active"
        assert classifier.classify_activity_level("very_active") == "active"
        
    # NEW: Habitual caffeine (UPDATED to match implementation)
    def test_classify_habitual_caffeine_naive(self):
        """Habitual < 50mg is naive."""
        from src.analysis.risk import SegmentClassifier
        classifier = SegmentClassifier()
        assert classifier.classify_habitual_caffeine(0.0) == "naive"
        assert classifier.classify_habitual_caffeine(49.0) == "naive"
        
    def test_classify_habitual_caffeine_moderate(self):
        """Habitual 50-299mg is moderate."""
        from src.analysis.risk import SegmentClassifier
        classifier = SegmentClassifier()
        assert classifier.classify_habitual_caffeine(50.0) == "moderate"
        assert classifier.classify_habitual_caffeine(150.0) == "moderate"
        assert classifier.classify_habitual_caffeine(299.0) == "moderate"
        
    def test_classify_habitual_caffeine_heavy(self):
        """Habitual >= 300mg is heavy."""
        from src.analysis.risk import SegmentClassifier
        classifier = SegmentClassifier()
        assert classifier.classify_habitual_caffeine(300.0) == "heavy"
        assert classifier.classify_habitual_caffeine(600.0) == "heavy"


# =============================================================================
# TEST: Risk Types
# =============================================================================

class TestRiskTypes:
    """Test risk type definitions."""
    
    def test_hyperglycemia_risk_defined(self):
        """Hyperglycemia risk type exists."""
        from src.analysis.risk import RiskType
        assert hasattr(RiskType, 'HYPERGLYCEMIA')
        
    def test_severe_hyperglycemia_risk_defined(self):
        """Severe hyperglycemia risk type exists."""
        from src.analysis.risk import RiskType
        assert hasattr(RiskType, 'SEVERE_HYPERGLYCEMIA')
        
    def test_jitter_risk_defined(self):
        """Jitter risk type exists."""
        from src.analysis.risk import RiskType
        assert hasattr(RiskType, 'JITTER')
        
    def test_sleep_disruption_risk_defined(self):
        """Sleep disruption risk type exists."""
        from src.analysis.risk import RiskType
        assert hasattr(RiskType, 'SLEEP_DISRUPTION')
        
    def test_crash_risk_defined(self):
        """Crash risk type exists."""
        from src.analysis.risk import RiskType
        assert hasattr(RiskType, 'CRASH')
        
    def test_hypoglycemia_risk_defined(self):
        """Hypoglycemia risk type exists."""
        from src.analysis.risk import RiskType
        assert hasattr(RiskType, 'HYPOGLYCEMIA')


# =============================================================================
# TEST: Risk Matrix
# =============================================================================

class TestRiskMatrix:
    """Test risk matrix functionality."""
    
    def test_risk_matrix_creation(self):
        """RiskMatrix can be created."""
        from src.analysis.risk import RiskMatrix
        matrix = RiskMatrix()
        assert matrix is not None
        
    def test_risk_matrix_dimensions(self):
        """RiskMatrix has correct structure."""
        from src.analysis.risk import RiskMatrix, SegmentationType, RiskType
        matrix = RiskMatrix()
        
        # Should have all segmentation types
        assert len(SegmentationType) == 6
        
        # Should have all risk types
        assert len(RiskType) >= 5
        
    def test_add_cell(self):
        """Can add risk value to matrix cell."""
        from src.analysis.risk import RiskMatrix, RiskMatrixCell, SegmentationType, RiskType
        
        matrix = RiskMatrix()
        cell = RiskMatrixCell(
            risk_percentage=25.0,
            population_percentage=15.0,
            count=150,
            is_danger_zone=True
        )
        matrix.add_cell(SegmentationType.BMI, "obese", RiskType.HYPERGLYCEMIA, cell)
        
        retrieved = matrix.get_cell(SegmentationType.BMI, "obese", RiskType.HYPERGLYCEMIA)
        assert retrieved is not None
        assert retrieved.risk_percentage == 25.0
        assert retrieved.population_percentage == 15.0
        assert retrieved.count == 150
        assert retrieved.is_danger_zone is True
        
    def test_get_segment_risks(self):
        """Can get all risks for a segment."""
        from src.analysis.risk import RiskMatrix, RiskMatrixCell, SegmentationType, RiskType
        
        matrix = RiskMatrix()
        
        # Add multiple risks for obese segment
        cell1 = RiskMatrixCell(risk_percentage=25.0, population_percentage=15.0, count=150)
        cell2 = RiskMatrixCell(risk_percentage=10.0, population_percentage=15.0, count=150)
        
        matrix.add_cell(SegmentationType.BMI, "obese", RiskType.HYPERGLYCEMIA, cell1)
        matrix.add_cell(SegmentationType.BMI, "obese", RiskType.JITTER, cell2)
        
        segment_risks = matrix.get_segment_risks(SegmentationType.BMI, "obese")
        
        assert len(segment_risks) == 2
        assert RiskType.HYPERGLYCEMIA in segment_risks
        assert RiskType.JITTER in segment_risks
        
    def test_get_risk_across_segments(self):
        """Can get a risk across all segments in a dimension."""
        from src.analysis.risk import RiskMatrix, RiskMatrixCell, SegmentationType, RiskType
        
        matrix = RiskMatrix()
        
        # Add same risk for different BMI segments
        cell1 = RiskMatrixCell(risk_percentage=5.0, population_percentage=40.0, count=400)
        cell2 = RiskMatrixCell(risk_percentage=15.0, population_percentage=35.0, count=350)
        cell3 = RiskMatrixCell(risk_percentage=25.0, population_percentage=25.0, count=250)
        
        matrix.add_cell(SegmentationType.BMI, "normal", RiskType.HYPERGLYCEMIA, cell1)
        matrix.add_cell(SegmentationType.BMI, "overweight", RiskType.HYPERGLYCEMIA, cell2)
        matrix.add_cell(SegmentationType.BMI, "obese", RiskType.HYPERGLYCEMIA, cell3)
        
        risk_by_segment = matrix.get_risk_by_segmentation(
            SegmentationType.BMI,
            RiskType.HYPERGLYCEMIA
        )
        
        assert "normal" in risk_by_segment
        assert "overweight" in risk_by_segment
        assert "obese" in risk_by_segment
        assert risk_by_segment["obese"].risk_percentage == 25.0


class TestRiskMatrixCell:
    """Test risk matrix cell."""
    
    def test_cell_is_immutable(self):
        """RiskMatrixCell is frozen."""
        from src.analysis.risk import RiskMatrixCell
        
        cell = RiskMatrixCell(
            risk_percentage=25.0,
            population_percentage=15.0,
            count=150
        )
        
        with pytest.raises(Exception):  # FrozenInstanceError
            cell.risk_percentage = 30.0
            
    def test_cell_danger_zone_flag(self):
        """RiskMatrixCell has danger zone flag."""
        from src.analysis.risk import RiskMatrixCell
        
        cell_safe = RiskMatrixCell(risk_percentage=10.0, population_percentage=20.0, count=200)
        assert cell_safe.is_danger_zone is False
        
        cell_danger = RiskMatrixCell(
            risk_percentage=30.0,
            population_percentage=20.0,
            count=200,
            is_danger_zone=True
        )
        assert cell_danger.is_danger_zone is True


# =============================================================================
# TEST: Danger Zone Detection
# =============================================================================

class TestDangerZoneDetection:
    """Test danger zone identification."""
    
    def test_danger_zone_threshold_default(self):
        """Default danger zone threshold is 25%."""
        from src.analysis.risk import DangerZoneDetector
        
        detector = DangerZoneDetector()
        assert detector.threshold == 25.0
        
    def test_danger_zone_threshold_custom(self):
        """Custom danger zone threshold can be set."""
        from src.analysis.risk import DangerZoneDetector
        
        detector = DangerZoneDetector(threshold=30.0)
        assert detector.threshold == 30.0
        
    def test_detect_danger_zone_above_threshold(self):
        """Values >= threshold are danger zones."""
        from src.analysis.risk import DangerZoneDetector
        
        detector = DangerZoneDetector(threshold=25.0)
        
        assert detector.is_danger_zone(25.0) is True
        assert detector.is_danger_zone(30.0) is True
        
    def test_detect_danger_zone_below_threshold(self):
        """Values < threshold are not danger zones."""
        from src.analysis.risk import DangerZoneDetector
        
        detector = DangerZoneDetector(threshold=25.0)
        
        assert detector.is_danger_zone(24.9) is False
        assert detector.is_danger_zone(10.0) is False
        
    def test_identify_all_danger_zones(self):
        """Can identify all danger zones in matrix."""
        from src.analysis.risk import (
            RiskMatrix, RiskMatrixCell, SegmentationType, RiskType,
            DangerZoneDetector
        )
        
        matrix = RiskMatrix()
        
        # Add cells with different risk levels
        cell_safe = RiskMatrixCell(
            risk_percentage=10.0,
            population_percentage=40.0,
            count=400,
            is_danger_zone=False
        )
        cell_danger = RiskMatrixCell(
            risk_percentage=30.0,
            population_percentage=15.0,
            count=150,
            is_danger_zone=True
        )
        
        matrix.add_cell(SegmentationType.BMI, "normal", RiskType.HYPERGLYCEMIA, cell_safe)
        matrix.add_cell(SegmentationType.BMI, "obese", RiskType.HYPERGLYCEMIA, cell_danger)
        
        detector = DangerZoneDetector(threshold=25.0)
        danger_zones = detector.find_danger_zones(matrix)
        
        assert len(danger_zones) == 1
        assert danger_zones[0].segment_value == "obese"
        assert danger_zones[0].risk_value == 30.0


# =============================================================================
# TEST: Full Risk Map Analyzer
# =============================================================================

class TestFullRiskMapAnalyzer:
    """Test the full risk map analyzer."""
    
    def test_analyzer_creation(self):
        """FullRiskMapAnalyzer can be created."""
        from src.analysis.risk import FullRiskMapAnalyzer
        
        analyzer = FullRiskMapAnalyzer()
        assert analyzer is not None
        
    def test_analyzer_uses_6_segmentations(self):
        """Analyzer supports 6 segmentation dimensions."""
        from src.analysis.risk import FullRiskMapAnalyzer, SegmentationType
        
        analyzer = FullRiskMapAnalyzer()
        
        # Verify all 6 segmentations exist in the enum
        assert len(SegmentationType) == 6
        assert hasattr(SegmentationType, 'BMI')
        assert hasattr(SegmentationType, 'AGE')
        assert hasattr(SegmentationType, 'CAFFEINE_SENSITIVITY')
        assert hasattr(SegmentationType, 'INSULIN_SENSITIVITY')
        assert hasattr(SegmentationType, 'ACTIVITY_LEVEL')
        assert hasattr(SegmentationType, 'HABITUAL_CAFFEINE')


# =============================================================================
# TEST: Risk Map Export
# =============================================================================

class TestRiskMapExport:
    """Test risk map export functionality."""
    
    def test_export_to_dict(self):
        """RiskMatrix can be exported to dictionary."""
        from src.analysis.risk import RiskMatrix, RiskMatrixCell, SegmentationType, RiskType
        
        matrix = RiskMatrix()
        matrix.total_population = 1000
        
        cell = RiskMatrixCell(
            risk_percentage=30.0,
            population_percentage=15.0,
            count=150,
            is_danger_zone=True
        )
        matrix.add_cell(SegmentationType.BMI, "obese", RiskType.HYPERGLYCEMIA, cell)
        
        exported = matrix.to_dict()
        
        assert "total_population" in exported
        assert exported["total_population"] == 1000
        assert "cells" in exported
        
    def test_get_table_for_segmentation(self):
        """Can get table format for PDF generation."""
        from src.analysis.risk import RiskMatrix, RiskMatrixCell, SegmentationType, RiskType
        
        matrix = RiskMatrix()
        
        # Add some test data
        for seg_val in ["normal", "overweight", "obese"]:
            for risk_type in [RiskType.HYPERGLYCEMIA, RiskType.JITTER]:
                cell = RiskMatrixCell(
                    risk_percentage=10.0 if seg_val == "normal" else 25.0,
                    population_percentage=33.0,
                    count=330
                )
                matrix.add_cell(SegmentationType.BMI, seg_val, risk_type, cell)
        
        table = matrix.get_table_for_segmentation(SegmentationType.BMI)
        
        assert "segmentation" in table
        assert "rows" in table
        assert "columns" in table
        assert "values" in table
        
        # Rows should be segment values
        assert "normal" in table["rows"]
        assert "overweight" in table["rows"]
        assert "obese" in table["rows"]


# =============================================================================
# TEST: Integration with RiskAnalyzer
# =============================================================================

class TestRiskMapIntegration:
    """Test integration with existing RiskAnalyzer."""
    
    def test_backwards_compatible_basic_analysis(self):
        """Original RiskAnalyzer.analyze() signature still works."""
        from src.analysis.risk import RiskAnalyzer, RiskAnalysisResult
        
        analyzer = RiskAnalyzer()
        
        # Use original API signature
        result = analyzer.analyze(
            risk_analysis={
                "pct_hyperglycemia": 15.0,
                "pct_sleep_disruption": 8.0
            },
            subgroup_analysis={
                "by_bmi": {
                    "normal": {"metrics": {"glucose_peak_mean": 130.0}, "pct": 50.0},
                    "obese": {"metrics": {"glucose_peak_mean": 160.0}, "pct": 20.0}
                }
            },
            n_individuals=1000
        )
        
        assert isinstance(result, RiskAnalysisResult)
        assert result.n_individuals == 1000


# =============================================================================
# TEST: Segment Values
# =============================================================================

class TestSegmentValues:
    """Test segment value definitions."""
    
    def test_bmi_segment_values(self):
        """BMI segment values are correct."""
        from src.analysis.risk import SEGMENT_VALUES, SegmentationType
        
        bmi_vals = SEGMENT_VALUES[SegmentationType.BMI]
        assert "normal" in bmi_vals
        assert "overweight" in bmi_vals
        assert "obese" in bmi_vals
        
    def test_age_segment_values(self):
        """Age segment values are correct."""
        from src.analysis.risk import SEGMENT_VALUES, SegmentationType
        
        age_vals = SEGMENT_VALUES[SegmentationType.AGE]
        assert "young" in age_vals
        assert "middle" in age_vals
        assert "older" in age_vals
        
    def test_caffeine_sensitivity_segment_values(self):
        """Caffeine sensitivity segment values are correct."""
        from src.analysis.risk import SEGMENT_VALUES, SegmentationType
        
        caff_vals = SEGMENT_VALUES[SegmentationType.CAFFEINE_SENSITIVITY]
        assert "slow" in caff_vals
        assert "normal" in caff_vals
        assert "fast" in caff_vals
        
    def test_insulin_sensitivity_segment_values(self):
        """Insulin sensitivity segment values are correct."""
        from src.analysis.risk import SEGMENT_VALUES, SegmentationType
        
        insulin_vals = SEGMENT_VALUES[SegmentationType.INSULIN_SENSITIVITY]
        assert "sensitive" in insulin_vals
        assert "normal" in insulin_vals
        assert "resistant" in insulin_vals
        
    def test_activity_level_segment_values(self):
        """Activity level segment values are correct."""
        from src.analysis.risk import SEGMENT_VALUES, SegmentationType
        
        activity_vals = SEGMENT_VALUES[SegmentationType.ACTIVITY_LEVEL]
        assert "sedentary" in activity_vals
        assert "moderate" in activity_vals
        assert "active" in activity_vals
        
    def test_habitual_caffeine_segment_values(self):
        """Habitual caffeine segment values are correct."""
        from src.analysis.risk import SEGMENT_VALUES, SegmentationType
        
        hab_vals = SEGMENT_VALUES[SegmentationType.HABITUAL_CAFFEINE]
        assert "naive" in hab_vals
        assert "moderate" in hab_vals
        assert "heavy" in hab_vals


# =============================================================================
# TEST: Convenience Functions
# =============================================================================

class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_format_risk_map_for_pdf(self):
        """format_risk_map_for_pdf produces correct structure."""
        from src.analysis.risk import (
            RiskMatrix, RiskMatrixCell, SegmentationType, RiskType,
            format_risk_map_for_pdf
        )
        
        matrix = RiskMatrix()
        
        # Add minimal test data
        cell = RiskMatrixCell(risk_percentage=15.0, population_percentage=33.0, count=330)
        matrix.add_cell(SegmentationType.BMI, "normal", RiskType.HYPERGLYCEMIA, cell)
        
        formatted = format_risk_map_for_pdf(matrix, SegmentationType.BMI)
        
        assert "title" in formatted
        assert "segments" in formatted
        assert "risks" in formatted
        assert "values" in formatted
        assert "danger_threshold" in formatted
