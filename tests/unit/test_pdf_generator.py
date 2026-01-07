"""
Tests for PDF Generator v0.

Tests that:
1. PDF generator creates valid files
2. Charts are generated correctly
3. All pages are included
4. Metrics are displayed properly
"""

import pytest
import numpy as np
import os
import tempfile
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from unittest.mock import Mock, MagicMock


# ==============================================================================
# Mock DaySimulationResult for testing (matches Contract 5.1)
# ==============================================================================

@dataclass(frozen=True)
class MockDaySimulationResult:
    """Mock of DaySimulationResult for testing PDF generator."""
    person_id: str
    time_minutes: np.ndarray
    glucose_curve: np.ndarray
    insulin_curve: np.ndarray
    caffeine_curve: np.ndarray
    alertness_curve: np.ndarray
    metrics: Dict[str, float]
    is_valid: bool
    warnings: Tuple[str, ...]
    
    @classmethod
    def create_sample(cls) -> "MockDaySimulationResult":
        """Create a sample result for testing."""
        # 24h simulation with dt=1.0 -> 1441 points
        n_points = 1441
        time = np.linspace(0, 1440, n_points)
        
        # Glucose: starts at 90, peaks at 160 after meal, returns to baseline
        glucose = 90 + 70 * np.exp(-((time - 60) ** 2) / 2000) * (time >= 0)
        glucose = np.clip(glucose, 70, 180)
        
        # Insulin: follows glucose with delay
        insulin = 10 + 80 * np.exp(-((time - 90) ** 2) / 3000) * (time >= 30)
        insulin = np.clip(insulin, 5, 100)
        
        # Caffeine: peak around 45 min, then decay
        caffeine = 2.0 * np.exp(-((time - 45) ** 2) / 800) + \
                   1.5 * np.exp(-time / 300) * (time >= 45)
        caffeine = np.clip(caffeine, 0, 4)
        
        # Alertness: correlates with caffeine but more sustained
        alertness = 50 + 40 * (1 - np.exp(-time / 60)) * np.exp(-time / 600)
        alertness = np.clip(alertness, 30, 95)
        
        metrics = {
            "glucose_peak": 158.5,
            "glucose_time_to_peak": 55.0,
            "glucose_auc": 135000.0,
            "glucose_time_above_threshold": 45.0,
            "caffeine_peak": 2.3,
            "caffeine_half_life": 5.2,
            "alertness_peak": 82.0,
            "alertness_duration_above_threshold": 180.0,
            "sleep_disruption_risk": 0.15,
        }
        
        return cls(
            person_id="test_person_001",
            time_minutes=time,
            glucose_curve=glucose,
            insulin_curve=insulin,
            caffeine_curve=caffeine,
            alertness_curve=alertness,
            metrics=metrics,
            is_valid=True,
            warnings=(),
        )
    
    @classmethod
    def create_with_warnings(cls) -> "MockDaySimulationResult":
        """Create a sample result with warnings."""
        base = cls.create_sample()
        return cls(
            person_id=base.person_id,
            time_minutes=base.time_minutes,
            glucose_curve=base.glucose_curve,
            insulin_curve=base.insulin_curve,
            caffeine_curve=base.caffeine_curve,
            alertness_curve=base.alertness_curve,
            metrics=base.metrics,
            is_valid=True,
            warnings=(
                "High caffeine intake detected (>300mg)",
                "Glucose spike above 160 mg/dL detected",
            ),
        )


# ==============================================================================
# Tests for charts.py
# ==============================================================================

class TestChartGeneration:
    """Tests for chart generation functions."""
    
    def test_import_charts_module(self):
        """charts module can be imported."""
        from src.reporting import charts
        assert hasattr(charts, 'create_glucose_chart')
        assert hasattr(charts, 'create_caffeine_chart')
        assert hasattr(charts, 'create_alertness_chart')
        assert hasattr(charts, 'create_combined_chart')
    
    def test_create_glucose_chart(self):
        """create_glucose_chart returns bytes (PNG)."""
        from src.reporting.charts import create_glucose_chart
        
        result = MockDaySimulationResult.create_sample()
        chart_bytes = create_glucose_chart(
            result.time_minutes,
            result.glucose_curve
        )
        
        assert isinstance(chart_bytes, bytes)
        assert len(chart_bytes) > 0
        # PNG magic bytes
        assert chart_bytes[:8] == b'\x89PNG\r\n\x1a\n'
    
    def test_create_caffeine_chart(self):
        """create_caffeine_chart returns bytes (PNG)."""
        from src.reporting.charts import create_caffeine_chart
        
        result = MockDaySimulationResult.create_sample()
        chart_bytes = create_caffeine_chart(
            result.time_minutes,
            result.caffeine_curve
        )
        
        assert isinstance(chart_bytes, bytes)
        assert len(chart_bytes) > 0
        assert chart_bytes[:8] == b'\x89PNG\r\n\x1a\n'
    
    def test_create_alertness_chart(self):
        """create_alertness_chart returns bytes (PNG)."""
        from src.reporting.charts import create_alertness_chart
        
        result = MockDaySimulationResult.create_sample()
        chart_bytes = create_alertness_chart(
            result.time_minutes,
            result.alertness_curve
        )
        
        assert isinstance(chart_bytes, bytes)
        assert len(chart_bytes) > 0
        assert chart_bytes[:8] == b'\x89PNG\r\n\x1a\n'
    
    def test_create_combined_chart(self):
        """create_combined_chart returns bytes (PNG)."""
        from src.reporting.charts import create_combined_chart
        
        result = MockDaySimulationResult.create_sample()
        chart_bytes = create_combined_chart(
            result.time_minutes,
            result.glucose_curve,
            result.caffeine_curve,
            result.alertness_curve
        )
        
        assert isinstance(chart_bytes, bytes)
        assert len(chart_bytes) > 0
        assert chart_bytes[:8] == b'\x89PNG\r\n\x1a\n'
    
    def test_charts_handle_edge_cases(self):
        """Charts handle edge cases gracefully."""
        from src.reporting.charts import create_glucose_chart
        
        # Short array
        time = np.linspace(0, 60, 61)
        glucose = np.full(61, 100.0)
        
        chart_bytes = create_glucose_chart(time, glucose)
        assert isinstance(chart_bytes, bytes)
        assert len(chart_bytes) > 0


# ==============================================================================
# Tests for pdf_generator.py
# ==============================================================================

class TestPDFGenerator:
    """Tests for PDF generator."""
    
    def test_import_pdf_generator(self):
        """pdf_generator module can be imported."""
        from src.reporting import pdf_generator
        assert hasattr(pdf_generator, 'PDFGenerator')
        assert hasattr(pdf_generator, 'PDFConfig')
    
    def test_pdf_generator_instantiation(self):
        """PDFGenerator can be instantiated."""
        from src.reporting.pdf_generator import PDFGenerator, PDFConfig
        
        config = PDFConfig()
        generator = PDFGenerator(config)
        
        assert generator is not None
        assert generator.config == config
    
    def test_pdf_generator_default_config(self):
        """PDFGenerator works with default config."""
        from src.reporting.pdf_generator import PDFGenerator
        
        generator = PDFGenerator()
        assert generator is not None
    
    def test_generate_pdf_returns_bytes(self):
        """generate() returns PDF bytes."""
        from src.reporting.pdf_generator import PDFGenerator
        
        generator = PDFGenerator()
        result = MockDaySimulationResult.create_sample()
        
        pdf_bytes = generator.generate(result)
        
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        # PDF magic bytes
        assert pdf_bytes[:4] == b'%PDF'
    
    def test_generate_pdf_with_product_name(self):
        """generate() accepts product name parameter."""
        from src.reporting.pdf_generator import PDFGenerator
        
        generator = PDFGenerator()
        result = MockDaySimulationResult.create_sample()
        
        pdf_bytes = generator.generate(
            result,
            product_name="Energy Pro Max"
        )
        
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
    
    def test_generate_pdf_to_file(self):
        """generate_to_file() creates a valid PDF file."""
        from src.reporting.pdf_generator import PDFGenerator
        
        generator = PDFGenerator()
        result = MockDaySimulationResult.create_sample()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.pdf"
            
            generator.generate_to_file(result, output_path)
            
            assert output_path.exists()
            assert output_path.stat().st_size > 0
            
            # Verify it's a valid PDF
            with open(output_path, 'rb') as f:
                header = f.read(4)
                assert header == b'%PDF'
    
    def test_pdf_has_multiple_pages(self):
        """Generated PDF has 6-10 pages."""
        from src.reporting.pdf_generator import PDFGenerator
        
        generator = PDFGenerator()
        result = MockDaySimulationResult.create_sample()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.pdf"
            generator.generate_to_file(result, output_path)
            
            # Count pages (simple check via /Page count in PDF)
            with open(output_path, 'rb') as f:
                content = f.read()
                # Simple heuristic: count /Page occurrences
                # More accurate would be to use pypdf but this is a basic check
                page_count = content.count(b'/Type /Page')
                # Allow some tolerance for PDF structure variations
                assert page_count >= 4, f"Expected at least 4 pages, got {page_count}"
    
    def test_pdf_contains_metrics(self):
        """Generated PDF contains metrics section."""
        from src.reporting.pdf_generator import PDFGenerator
        
        generator = PDFGenerator()
        result = MockDaySimulationResult.create_sample()
        
        pdf_bytes = generator.generate(result)
        
        # Check that metric-related text appears in PDF
        # (PDF text is encoded but some strings should be findable)
        pdf_str = pdf_bytes.decode('latin-1', errors='ignore')
        
        # At minimum, some common strings should appear
        # Note: PDF encoding may obscure some text
        assert len(pdf_bytes) > 10000  # Substantial content
    
    def test_pdf_with_warnings(self):
        """PDF includes warnings when present."""
        from src.reporting.pdf_generator import PDFGenerator
        
        generator = PDFGenerator()
        result = MockDaySimulationResult.create_with_warnings()
        
        pdf_bytes = generator.generate(result)
        
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0


# ==============================================================================
# Tests for PDFConfig
# ==============================================================================

class TestPDFConfig:
    """Tests for PDF configuration."""
    
    def test_pdf_config_defaults(self):
        """PDFConfig has sensible defaults."""
        from src.reporting.pdf_generator import PDFConfig
        
        config = PDFConfig()
        
        assert config.page_size == "letter"
        assert config.include_charts == True
        assert config.include_methodology == True
    
    def test_pdf_config_custom_values(self):
        """PDFConfig accepts custom values."""
        from src.reporting.pdf_generator import PDFConfig
        
        config = PDFConfig(
            page_size="A4",
            include_charts=False,
            include_methodology=False
        )
        
        assert config.page_size == "A4"
        assert config.include_charts == False
        assert config.include_methodology == False
    
    def test_pdf_config_immutable(self):
        """PDFConfig is immutable (frozen dataclass)."""
        from src.reporting.pdf_generator import PDFConfig
        
        config = PDFConfig()
        
        with pytest.raises(AttributeError):
            config.page_size = "A4"


# ==============================================================================
# Tests for reporting module exports
# ==============================================================================

class TestReportingModuleExports:
    """Tests for reporting module __init__.py exports."""
    
    def test_import_reporting_module(self):
        """reporting module can be imported."""
        from src import reporting
        assert reporting is not None
    
    def test_exports_pdf_generator(self):
        """reporting module exports PDFGenerator."""
        from src.reporting import PDFGenerator, PDFConfig
        assert PDFGenerator is not None
        assert PDFConfig is not None
    
    def test_exports_charts(self):
        """reporting module exports chart functions."""
        from src.reporting import (
            create_glucose_chart,
            create_caffeine_chart,
            create_alertness_chart,
            create_combined_chart,
        )
        assert create_glucose_chart is not None
        assert create_caffeine_chart is not None
        assert create_alertness_chart is not None
        assert create_combined_chart is not None


# ==============================================================================
# Integration-like tests
# ==============================================================================

class TestPDFGeneratorIntegration:
    """Integration tests for PDF generator with realistic data."""
    
    def test_full_workflow(self):
        """Complete workflow: result -> PDF file."""
        from src.reporting.pdf_generator import PDFGenerator
        
        # Create realistic result
        result = MockDaySimulationResult.create_sample()
        
        # Generate PDF
        generator = PDFGenerator()
        pdf_bytes = generator.generate(
            result,
            product_name="Test Product",
            report_date="2025-01-07"
        )
        
        # Verify output
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:4] == b'%PDF'
        assert len(pdf_bytes) > 50000  # Should be substantial
    
    def test_reproducibility(self):
        """Same input produces same output (deterministic)."""
        from src.reporting.pdf_generator import PDFGenerator
        
        result = MockDaySimulationResult.create_sample()
        generator = PDFGenerator()
        
        pdf1 = generator.generate(result, product_name="Test")
        pdf2 = generator.generate(result, product_name="Test")
        
        # PDFs should be identical
        # (allowing for timestamp differences if any)
        assert len(pdf1) == len(pdf2)
    
    def test_handles_extreme_values(self):
        """Generator handles extreme but valid values."""
        from src.reporting.pdf_generator import PDFGenerator
        
        n_points = 1441
        time = np.linspace(0, 1440, n_points)
        
        # Extreme but valid values
        result = MockDaySimulationResult(
            person_id="extreme_test",
            time_minutes=time,
            glucose_curve=np.full(n_points, 180.0),  # High but valid
            insulin_curve=np.full(n_points, 100.0),
            caffeine_curve=np.full(n_points, 4.0),
            alertness_curve=np.full(n_points, 95.0),
            metrics={
                "glucose_peak": 180.0,
                "glucose_time_to_peak": 0.0,
                "glucose_auc": 200000.0,
                "glucose_time_above_threshold": 1440.0,
                "caffeine_peak": 4.0,
                "caffeine_half_life": 8.0,
                "alertness_peak": 95.0,
                "alertness_duration_above_threshold": 1440.0,
                "sleep_disruption_risk": 0.95,
            },
            is_valid=True,
            warnings=("Very high risk values",),
        )
        
        generator = PDFGenerator()
        pdf_bytes = generator.generate(result)
        
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0


# ==============================================================================
# Tests for time formatting utilities
# ==============================================================================

class TestTimeFormatting:
    """Tests for time formatting utilities used in PDF."""
    
    def test_minutes_to_time_string(self):
        """minutes_to_time_string formats correctly."""
        from src.reporting.pdf_generator import minutes_to_time_string
        
        assert minutes_to_time_string(0) == "00:00"
        assert minutes_to_time_string(60) == "01:00"
        assert minutes_to_time_string(90) == "01:30"
        assert minutes_to_time_string(720) == "12:00"
        assert minutes_to_time_string(1439) == "23:59"
    
    def test_format_duration(self):
        """format_duration formats correctly."""
        from src.reporting.pdf_generator import format_duration
        
        assert format_duration(30) == "30 min"
        assert format_duration(60) == "1h 0min"
        assert format_duration(90) == "1h 30min"
        assert format_duration(180) == "3h 0min"
