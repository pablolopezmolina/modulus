"""
Tests for PDF Generator v1 (20-page professional report).
Sesión 7.1: PDF v1 Completo
"""

import pytest
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Any
from datetime import datetime
import tempfile
import os


# =============================================================================
# MOCK CLASSES FOR TESTING
# =============================================================================

@dataclass(frozen=True)
class RiskSummary:
    risk_name: str
    value: float
    threshold: float
    level: str
    def to_dict(self) -> Dict[str, Any]:
        return {"risk_name": self.risk_name, "value": self.value, "threshold": self.threshold, "level": self.level}

@dataclass(frozen=True)
class SegmentAtRisk:
    segment_name: str
    dimension: str
    risk_name: str
    percentage: float
    def to_dict(self) -> Dict[str, Any]:
        return {"segment_name": self.segment_name, "dimension": self.dimension, "risk_name": self.risk_name, "percentage": self.percentage}

@dataclass(frozen=True)
class Decision:
    verdict: str
    confidence: float
    top_risks: tuple
    segments_at_risk: tuple
    summary: str
    @property
    def is_acceptable(self) -> bool:
        return self.verdict != "NO_GO"
    def to_dict(self) -> Dict[str, Any]:
        return {"verdict": self.verdict, "confidence": self.confidence, "summary": self.summary}

@dataclass(frozen=True)
class ClaimAnalysis:
    claim_id: str
    claim_text: str
    is_defensible: bool
    confidence: float
    responder_percentage: float
    supporting_metrics: Dict[str, float]
    methodology: str
    efsa_compatible: bool
    fda_compatible: bool
    suggested_wording: str
    def to_dict(self) -> Dict[str, Any]:
        return {"claim_id": self.claim_id, "is_defensible": self.is_defensible, "confidence": self.confidence}

@dataclass
class ClaimAnalysisResult:
    claims: Dict[str, ClaimAnalysis]
    def get_defensible_claims(self) -> List[ClaimAnalysis]:
        return [c for c in self.claims.values() if c.is_defensible]
    def to_dict(self) -> Dict[str, Any]:
        return {k: v.to_dict() for k, v in self.claims.items()}

@dataclass(frozen=True)
class RiskMetric:
    name: str
    value: float
    threshold: float
    level: str
    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "value": self.value, "threshold": self.threshold, "level": self.level}

@dataclass(frozen=True)
class DangerZone:
    segment_name: str
    dimension: str
    risk_name: str
    percentage: float
    severity_score: float
    recommendation: str
    def to_dict(self) -> Dict[str, Any]:
        return {"segment_name": self.segment_name, "risk_name": self.risk_name, "percentage": self.percentage}

@dataclass
class RiskMap:
    matrices: Dict[str, Dict[str, Dict[str, float]]]
    def to_dict(self) -> Dict[str, Any]:
        return {"matrices": self.matrices}

@dataclass
class RiskAnalysisResult:
    overall_risks: List[RiskMetric]
    risk_map: RiskMap
    danger_zones: List[DangerZone]
    def get_top_risks(self, n: int = 5) -> List[RiskMetric]:
        return sorted(self.overall_risks, key=lambda r: r.value, reverse=True)[:n]
    def to_dict(self) -> Dict[str, Any]:
        return {"overall_risks": [r.to_dict() for r in self.overall_risks]}

@dataclass
class PopulationDayResult:
    n_individuals: int
    n_valid: int
    time_minutes: np.ndarray
    glucose_percentiles: Dict[str, np.ndarray]
    caffeine_percentiles: Dict[str, np.ndarray]
    alertness_percentiles: Dict[str, np.ndarray]
    metrics_stats: Dict[str, Dict[str, float]]
    risk_analysis: Dict[str, float]
    subgroup_analysis: Dict[str, Dict[str, Any]]
    def to_dict(self) -> Dict[str, Any]:
        return {"n_individuals": self.n_individuals, "n_valid": self.n_valid}

@dataclass(frozen=True)
class Ingredient:
    compound_id: str
    amount: float
    unit: str

@dataclass(frozen=True)
class Formulation:
    name: str
    ingredients: tuple
    form: str
    brand: str = ""
    description: str = ""
    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "form": self.form, "brand": self.brand}


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_time_array():
    return np.arange(0, 1441, dtype=float)

@pytest.fixture
def sample_glucose_percentiles(sample_time_array):
    n = len(sample_time_array)
    base = 90 + 20 * np.sin(np.linspace(0, 2*np.pi, n))
    return {"p5": base - 10, "p25": base - 5, "p50": base, "p75": base + 5, "p95": base + 15}

@pytest.fixture
def sample_caffeine_percentiles(sample_time_array):
    n = len(sample_time_array)
    caffeine = np.zeros(n)
    for i in range(420, n):
        caffeine[i] = 2.0 * np.exp(-(i - 420) / 300)
    return {"p5": caffeine * 0.7, "p25": caffeine * 0.85, "p50": caffeine, "p75": caffeine * 1.15, "p95": caffeine * 1.4}

@pytest.fixture
def sample_alertness_percentiles(sample_time_array):
    n = len(sample_time_array)
    alertness = 50 * np.ones(n)
    for i in range(420, min(900, n)):
        alertness[i] = min(100, 50 + 25 * (1 - ((i - 420) / 480) ** 2))
    return {"p5": alertness - 15, "p25": alertness - 8, "p50": alertness, "p75": alertness + 8, "p95": alertness + 15}

@pytest.fixture
def sample_population_result(sample_time_array, sample_glucose_percentiles, sample_caffeine_percentiles, sample_alertness_percentiles):
    return PopulationDayResult(
        n_individuals=1000, n_valid=985, time_minutes=sample_time_array,
        glucose_percentiles=sample_glucose_percentiles, caffeine_percentiles=sample_caffeine_percentiles,
        alertness_percentiles=sample_alertness_percentiles,
        metrics_stats={"glucose_peak": {"mean": 132.5, "std": 18.2}, "alertness_peak": {"mean": 72.0, "std": 8.5}},
        risk_analysis={"pct_hyperglycemia": 12.5, "pct_sleep_disruption": 18.7, "pct_jitter_risk": 8.3},
        subgroup_analysis={"by_bmi": {"normal": {"n": 450}, "obese": {"n": 200}}}
    )

@pytest.fixture
def sample_decision():
    return Decision(
        verdict="CAUTION", confidence=0.75,
        top_risks=(RiskSummary("pct_sleep_disruption", 18.7, 10.0, "MEDIUM"),),
        segments_at_risk=(SegmentAtRisk("slow", "caffeine_sensitivity", "pct_sleep_disruption", 32.0),),
        summary="Sleep disruption risk of 18.7% exceeds threshold."
    )

@pytest.fixture
def sample_risk_analysis():
    return RiskAnalysisResult(
        overall_risks=[RiskMetric("pct_hyperglycemia", 12.5, 10.0, "MEDIUM"), RiskMetric("pct_sleep_disruption", 18.7, 10.0, "MEDIUM")],
        risk_map=RiskMap(matrices={"by_bmi": {"normal": {"pct_hyperglycemia": 8.0}, "obese": {"pct_hyperglycemia": 22.0}}}),
        danger_zones=[DangerZone("slow", "caffeine_sensitivity", "pct_sleep_disruption", 32.0, 0.85, "Reduce caffeine.")]
    )

@pytest.fixture
def sample_claims():
    return ClaimAnalysisResult(claims={
        "sustained_energy": ClaimAnalysis("sustained_energy", "Sustained Energy", True, 0.82, 73.0, {}, "", False, False, "Helps maintain energy"),
        "no_crash": ClaimAnalysis("no_crash", "No Crash", True, 0.91, 94.8, {}, "", False, False, "Gentle energy"),
        "quick_onset": ClaimAnalysis("quick_onset", "Quick Onset", False, 0.45, 42.0, {}, "", False, False, ""),
    })

@pytest.fixture
def sample_formulation():
    return Formulation(
        name="Energy Pro Max",
        ingredients=(Ingredient("caffeine", 200.0, "mg"), Ingredient("l_theanine", 100.0, "mg")),
        form="powder", brand="ClientCorp", description="Premium pre-workout"
    )


# =============================================================================
# TESTS
# =============================================================================

class TestPDFReportInput:
    def test_creation(self, sample_formulation, sample_population_result, sample_decision, sample_risk_analysis, sample_claims):
        from src.reporting.pdf_generator import PDFReportInput
        report = PDFReportInput(
            formulation=sample_formulation, population_result=sample_population_result, decision=sample_decision,
            risk_analysis=sample_risk_analysis, claim_analysis=sample_claims,
            report_date=datetime.now(), report_id="RPT-001", client_name="ClientCorp"
        )
        assert report.formulation.name == "Energy Pro Max"
        assert report.decision.verdict == "CAUTION"

    def test_to_dict(self, sample_formulation, sample_population_result, sample_decision, sample_risk_analysis, sample_claims):
        from src.reporting.pdf_generator import PDFReportInput
        report = PDFReportInput(
            formulation=sample_formulation, population_result=sample_population_result, decision=sample_decision,
            risk_analysis=sample_risk_analysis, claim_analysis=sample_claims,
            report_date=datetime.now(), report_id="RPT-001", client_name="ClientCorp"
        )
        data = report.to_dict()
        assert "formulation" in data
        assert "report_id" in data


class TestPDFGeneratorV1:
    def test_creation(self):
        from src.reporting.pdf_generator import PDFGeneratorV1
        gen = PDFGeneratorV1()
        assert gen is not None

    def test_with_config(self):
        from src.reporting.pdf_generator import PDFGeneratorV1, PDFConfig
        config = PDFConfig(page_size="A4", include_charts=True)
        gen = PDFGeneratorV1(config=config)
        assert gen.config.page_size == "A4"

    def test_generates_file(self, sample_formulation, sample_population_result, sample_decision, sample_risk_analysis, sample_claims):
        from src.reporting.pdf_generator import PDFGeneratorV1, PDFReportInput
        report = PDFReportInput(
            formulation=sample_formulation, population_result=sample_population_result, decision=sample_decision,
            risk_analysis=sample_risk_analysis, claim_analysis=sample_claims,
            report_date=datetime.now(), report_id="RPT-001", client_name="ClientCorp"
        )
        gen = PDFGeneratorV1()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "report.pdf")
            result = gen.generate(report, path)
            assert result.success is True
            assert os.path.exists(path)
            assert os.path.getsize(path) > 0

    def test_returns_metadata(self, sample_formulation, sample_population_result, sample_decision, sample_risk_analysis, sample_claims):
        from src.reporting.pdf_generator import PDFGeneratorV1, PDFReportInput
        report = PDFReportInput(
            formulation=sample_formulation, population_result=sample_population_result, decision=sample_decision,
            risk_analysis=sample_risk_analysis, claim_analysis=sample_claims,
            report_date=datetime.now(), report_id="RPT-001", client_name="ClientCorp"
        )
        gen = PDFGeneratorV1()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "report.pdf")
            result = gen.generate(report, path)
            assert result.page_count >= 15
            assert result.generation_time_seconds > 0


class TestPDFPages:
    def test_cover_page(self, sample_formulation, sample_population_result, sample_decision, sample_risk_analysis, sample_claims):
        from src.reporting.pdf_generator import PDFGeneratorV1, PDFReportInput
        report = PDFReportInput(
            formulation=sample_formulation, population_result=sample_population_result, decision=sample_decision,
            risk_analysis=sample_risk_analysis, claim_analysis=sample_claims,
            report_date=datetime.now(), report_id="RPT-001", client_name="ClientCorp"
        )
        gen = PDFGeneratorV1()
        cover = gen._generate_cover_page(report)
        assert "MODULUS" in cover.title
        assert report.formulation.name in cover.product_name

    def test_decision_page_caution(self, sample_formulation, sample_population_result, sample_decision, sample_risk_analysis, sample_claims):
        from src.reporting.pdf_generator import PDFGeneratorV1, PDFReportInput
        report = PDFReportInput(
            formulation=sample_formulation, population_result=sample_population_result, decision=sample_decision,
            risk_analysis=sample_risk_analysis, claim_analysis=sample_claims,
            report_date=datetime.now(), report_id="RPT-001", client_name="ClientCorp"
        )
        gen = PDFGeneratorV1()
        page = gen._generate_decision_page(report)
        assert page.verdict == "CAUTION"
        assert page.verdict_color in ["yellow", "orange", "#FFA500"]

    def test_decision_page_go_is_green(self, sample_formulation, sample_population_result, sample_risk_analysis, sample_claims):
        from src.reporting.pdf_generator import PDFGeneratorV1, PDFReportInput
        go_decision = Decision(verdict="GO", confidence=0.92, top_risks=(), segments_at_risk=(), summary="All good.")
        report = PDFReportInput(
            formulation=sample_formulation, population_result=sample_population_result, decision=go_decision,
            risk_analysis=sample_risk_analysis, claim_analysis=sample_claims,
            report_date=datetime.now(), report_id="RPT-001", client_name="ClientCorp"
        )
        gen = PDFGeneratorV1()
        page = gen._generate_decision_page(report)
        assert page.verdict == "GO"
        assert page.verdict_color in ["green", "#00AA00", "#008000"]

    def test_decision_page_nogo_is_red(self, sample_formulation, sample_population_result, sample_risk_analysis, sample_claims):
        from src.reporting.pdf_generator import PDFGeneratorV1, PDFReportInput
        nogo = Decision(verdict="NO_GO", confidence=0.88, top_risks=(), segments_at_risk=(), summary="Fail.")
        report = PDFReportInput(
            formulation=sample_formulation, population_result=sample_population_result, decision=nogo,
            risk_analysis=sample_risk_analysis, claim_analysis=sample_claims,
            report_date=datetime.now(), report_id="RPT-001", client_name="ClientCorp"
        )
        gen = PDFGeneratorV1()
        page = gen._generate_decision_page(report)
        assert page.verdict == "NO_GO"
        assert page.verdict_color in ["red", "#FF0000", "#AA0000"]

    def test_claims_page(self, sample_formulation, sample_population_result, sample_decision, sample_risk_analysis, sample_claims):
        from src.reporting.pdf_generator import PDFGeneratorV1, PDFReportInput
        report = PDFReportInput(
            formulation=sample_formulation, population_result=sample_population_result, decision=sample_decision,
            risk_analysis=sample_risk_analysis, claim_analysis=sample_claims,
            report_date=datetime.now(), report_id="RPT-001", client_name="ClientCorp"
        )
        gen = PDFGeneratorV1()
        page = gen._generate_claims_pages(report)
        defensible = [c for c in page.claims if c.is_defensible]
        assert len(defensible) == 2

    def test_risk_page(self, sample_formulation, sample_population_result, sample_decision, sample_risk_analysis, sample_claims):
        from src.reporting.pdf_generator import PDFGeneratorV1, PDFReportInput
        report = PDFReportInput(
            formulation=sample_formulation, population_result=sample_population_result, decision=sample_decision,
            risk_analysis=sample_risk_analysis, claim_analysis=sample_claims,
            report_date=datetime.now(), report_id="RPT-001", client_name="ClientCorp"
        )
        gen = PDFGeneratorV1()
        page = gen._generate_risk_pages(report)
        assert page.risk_map is not None
        assert len(page.danger_zones) > 0


class TestChartGeneration:
    def test_glucose_chart(self, sample_population_result):
        from src.reporting.charts import ChartGenerator
        gen = ChartGenerator()
        chart = gen.create_glucose_chart(sample_population_result.time_minutes, sample_population_result.glucose_percentiles)
        assert chart is not None

    def test_caffeine_chart(self, sample_population_result):
        from src.reporting.charts import ChartGenerator
        gen = ChartGenerator()
        chart = gen.create_caffeine_chart(sample_population_result.time_minutes, sample_population_result.caffeine_percentiles)
        assert chart is not None

    def test_alertness_chart(self, sample_population_result):
        from src.reporting.charts import ChartGenerator
        gen = ChartGenerator()
        chart = gen.create_alertness_chart(sample_population_result.time_minutes, sample_population_result.alertness_percentiles)
        assert chart is not None

    def test_risk_heatmap(self, sample_risk_analysis):
        from src.reporting.charts import ChartGenerator
        gen = ChartGenerator()
        chart = gen.create_risk_heatmap(sample_risk_analysis.risk_map)
        assert chart is not None


class TestPDFStructure:
    def test_minimum_pages(self, sample_formulation, sample_population_result, sample_decision, sample_risk_analysis, sample_claims):
        from src.reporting.pdf_generator import PDFGeneratorV1, PDFReportInput
        report = PDFReportInput(
            formulation=sample_formulation, population_result=sample_population_result, decision=sample_decision,
            risk_analysis=sample_risk_analysis, claim_analysis=sample_claims,
            report_date=datetime.now(), report_id="RPT-001", client_name="ClientCorp"
        )
        gen = PDFGeneratorV1()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = gen.generate(report, os.path.join(tmpdir, "report.pdf"))
            assert result.page_count >= 15

    def test_sections_order(self, sample_formulation, sample_population_result, sample_decision, sample_risk_analysis, sample_claims):
        from src.reporting.pdf_generator import PDFGeneratorV1, PDFReportInput
        report = PDFReportInput(
            formulation=sample_formulation, population_result=sample_population_result, decision=sample_decision,
            risk_analysis=sample_risk_analysis, claim_analysis=sample_claims,
            report_date=datetime.now(), report_id="RPT-001", client_name="ClientCorp"
        )
        gen = PDFGeneratorV1()
        sections = gen.get_sections_list()
        names = [s.name.lower() for s in sections]
        assert any("cover" in n for n in names)
        assert any("decision" in n for n in names)
        assert any("risk" in n for n in names)


class TestEdgeCases:
    def test_empty_danger_zones(self, sample_formulation, sample_population_result, sample_decision, sample_claims):
        from src.reporting.pdf_generator import PDFGeneratorV1, PDFReportInput
        safe_risk = RiskAnalysisResult(overall_risks=[], risk_map=RiskMap(matrices={}), danger_zones=[])
        report = PDFReportInput(
            formulation=sample_formulation, population_result=sample_population_result, decision=sample_decision,
            risk_analysis=safe_risk, claim_analysis=sample_claims,
            report_date=datetime.now(), report_id="RPT-001", client_name="ClientCorp"
        )
        gen = PDFGeneratorV1()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = gen.generate(report, os.path.join(tmpdir, "report.pdf"))
            assert result.success is True

    def test_single_ingredient(self, sample_population_result, sample_decision, sample_risk_analysis, sample_claims):
        from src.reporting.pdf_generator import PDFGeneratorV1, PDFReportInput
        simple = Formulation(name="Pure Caffeine", ingredients=(Ingredient("caffeine", 100.0, "mg"),), form="capsule", brand="Test")
        report = PDFReportInput(
            formulation=simple, population_result=sample_population_result, decision=sample_decision,
            risk_analysis=sample_risk_analysis, claim_analysis=sample_claims,
            report_date=datetime.now(), report_id="RPT-001", client_name="Test"
        )
        gen = PDFGeneratorV1()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = gen.generate(report, os.path.join(tmpdir, "report.pdf"))
            assert result.success is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
