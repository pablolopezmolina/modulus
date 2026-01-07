"""
MODULUS Reporting Module.

Sesión 7.1: PDF v1 Completo
"""

from .pdf_generator import (
    PDFConfig,
    PDFReportInput,
    PDFGenerationResult,
    PDFGeneratorV1,
)
from .charts import ChartGenerator, ChartMetadata

__all__ = [
    "PDFConfig",
    "PDFReportInput", 
    "PDFGenerationResult",
    "PDFGeneratorV1",
    "ChartGenerator",
    "ChartMetadata",
]
