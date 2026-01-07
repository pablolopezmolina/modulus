"""
MODULUS Reporting Module

This module provides PDF report generation capabilities for simulation results.
Part of CAPA 7 (Output & Delivery) in the MODULUS architecture.

Main exports:
- PDFGenerator: Main class for generating PDF reports
- PDFConfig: Configuration for PDF generation
- Chart functions: For embedding charts in reports

Example usage:
    from src.reporting import PDFGenerator, PDFConfig
    
    generator = PDFGenerator()
    pdf_bytes = generator.generate(result, product_name="My Product")
    
    # Or with custom config
    config = PDFConfig(page_size="A4", include_methodology=False)
    generator = PDFGenerator(config)
    generator.generate_to_file(result, Path("report.pdf"))
"""

from .pdf_generator import (
    PDFGenerator,
    PDFConfig,
    minutes_to_time_string,
    format_duration,
    format_metric_value,
)

from .charts import (
    create_glucose_chart,
    create_caffeine_chart,
    create_alertness_chart,
    create_combined_chart,
    create_metrics_summary_chart,
)

__all__ = [
    # PDF Generator
    'PDFGenerator',
    'PDFConfig',
    
    # Utility functions
    'minutes_to_time_string',
    'format_duration',
    'format_metric_value',
    
    # Chart functions
    'create_glucose_chart',
    'create_caffeine_chart',
    'create_alertness_chart',
    'create_combined_chart',
    'create_metrics_summary_chart',
]
