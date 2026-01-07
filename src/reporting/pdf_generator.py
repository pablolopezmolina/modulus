"""
MODULUS PDF Generator v0

Generates professional PDF reports from simulation results.
This is the core product output - what clients pay €50k+ for.

This module is part of src/reporting/ (CAPA 7 - Output & Delivery).

PDF v0 Structure (6-10 pages):
1. Executive Summary (1 page)
2-3. 24h Curves (2 pages)
4. Key Metrics (1 page)
5. Warnings (1 page)
6. Methodology Brief (1 page)
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, Union, List, Tuple
from pathlib import Path
import io
from datetime import datetime

import numpy as np

# ReportLab imports
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak,
    Table, TableStyle, KeepTogether
)
from reportlab.lib import colors

# Local imports
from .charts import (
    create_glucose_chart,
    create_caffeine_chart,
    create_alertness_chart,
    create_combined_chart,
    create_metrics_summary_chart,
)


# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================

def minutes_to_time_string(minutes: float) -> str:
    """Convert minutes from midnight to HH:MM format."""
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    return f"{hours:02d}:{mins:02d}"


def format_duration(minutes: float) -> str:
    """Format duration in minutes to human-readable string."""
    if minutes < 60:
        return f"{int(minutes)} min"
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    return f"{hours}h {mins}min"


def format_metric_value(name: str, value: float) -> str:
    """Format a metric value for display."""
    if 'risk' in name.lower() or 'percentage' in name.lower():
        return f"{value * 100:.1f}%"
    elif 'time' in name.lower() and 'threshold' not in name.lower():
        return format_duration(value)
    elif 'half_life' in name.lower():
        return f"{value:.1f}h"
    elif 'auc' in name.lower():
        return f"{value:.0f}"
    else:
        return f"{value:.1f}"


# ==============================================================================
# CONFIGURATION
# ==============================================================================

@dataclass(frozen=True)
class PDFConfig:
    """Configuration for PDF generation."""
    
    # Page settings
    page_size: str = "letter"  # "letter" or "A4"
    
    # Content options
    include_charts: bool = True
    include_methodology: bool = True
    include_warnings: bool = True
    
    # Branding
    company_name: str = "MODULUS"
    tagline: str = "Decision & Compliance OS"
    
    # Colors (hex)
    primary_color: str = "#2E86AB"
    secondary_color: str = "#1A365D"
    accent_color: str = "#F18F01"
    warning_color: str = "#EF4444"
    success_color: str = "#10B981"
    
    def get_page_size(self) -> tuple:
        """Get reportlab page size tuple."""
        if self.page_size.lower() == "a4":
            return A4
        return letter


# ==============================================================================
# STYLES
# ==============================================================================

def get_custom_styles(config: PDFConfig) -> Dict[str, ParagraphStyle]:
    """Create custom paragraph styles for the PDF."""
    base_styles = getSampleStyleSheet()
    
    custom_styles = {}
    
    # Title style
    custom_styles['CustomTitle'] = ParagraphStyle(
        'CustomTitle',
        parent=base_styles['Title'],
        fontSize=24,
        textColor=HexColor(config.secondary_color),
        spaceAfter=20,
        alignment=TA_CENTER,
    )
    
    # Subtitle
    custom_styles['Subtitle'] = ParagraphStyle(
        'Subtitle',
        parent=base_styles['Normal'],
        fontSize=14,
        textColor=HexColor(config.primary_color),
        spaceAfter=30,
        alignment=TA_CENTER,
    )
    
    # Section heading
    custom_styles['SectionHeading'] = ParagraphStyle(
        'SectionHeading',
        parent=base_styles['Heading1'],
        fontSize=16,
        textColor=HexColor(config.secondary_color),
        spaceBefore=20,
        spaceAfter=12,
        borderColor=HexColor(config.primary_color),
        borderWidth=0,
        borderPadding=5,
    )
    
    # Subsection heading
    custom_styles['SubsectionHeading'] = ParagraphStyle(
        'SubsectionHeading',
        parent=base_styles['Heading2'],
        fontSize=12,
        textColor=HexColor(config.primary_color),
        spaceBefore=15,
        spaceAfter=8,
    )
    
    # Body text
    custom_styles['BodyText'] = ParagraphStyle(
        'BodyText',
        parent=base_styles['Normal'],
        fontSize=10,
        leading=14,
        alignment=TA_JUSTIFY,
        spaceAfter=10,
    )
    
    # Warning text
    custom_styles['Warning'] = ParagraphStyle(
        'Warning',
        parent=base_styles['Normal'],
        fontSize=10,
        textColor=HexColor(config.warning_color),
        spaceBefore=5,
        spaceAfter=5,
        leftIndent=20,
        bulletIndent=10,
    )
    
    # Metric label
    custom_styles['MetricLabel'] = ParagraphStyle(
        'MetricLabel',
        parent=base_styles['Normal'],
        fontSize=9,
        textColor=colors.gray,
    )
    
    # Metric value
    custom_styles['MetricValue'] = ParagraphStyle(
        'MetricValue',
        parent=base_styles['Normal'],
        fontSize=14,
        textColor=HexColor(config.secondary_color),
        fontName='Helvetica-Bold',
    )
    
    # Footer
    custom_styles['Footer'] = ParagraphStyle(
        'Footer',
        parent=base_styles['Normal'],
        fontSize=8,
        textColor=colors.gray,
        alignment=TA_CENTER,
    )
    
    return custom_styles


# ==============================================================================
# PDF GENERATOR CLASS
# ==============================================================================

class PDFGenerator:
    """
    Generates professional PDF reports from DaySimulationResult.
    
    Usage:
        generator = PDFGenerator()
        pdf_bytes = generator.generate(result, product_name="My Product")
        
        # Or save to file
        generator.generate_to_file(result, Path("report.pdf"))
    """
    
    def __init__(self, config: Optional[PDFConfig] = None):
        """
        Initialize PDF generator.
        
        Args:
            config: PDF configuration. Uses defaults if not provided.
        """
        self.config = config or PDFConfig()
        self.styles = get_custom_styles(self.config)
    
    def generate(
        self,
        result: Any,  # DaySimulationResult or compatible
        product_name: str = "Unnamed Product",
        report_date: Optional[str] = None,
    ) -> bytes:
        """
        Generate PDF report from simulation result.
        
        Args:
            result: DaySimulationResult with simulation data
            product_name: Name of the product being analyzed
            report_date: Report date (defaults to today)
            
        Returns:
            PDF file as bytes
        """
        if report_date is None:
            report_date = datetime.now().strftime("%Y-%m-%d")
        
        # Create PDF in memory
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=self.config.get_page_size(),
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )
        
        # Build story (list of flowables)
        story = []
        
        # Page 1: Executive Summary
        story.extend(self._create_executive_summary(result, product_name, report_date))
        story.append(PageBreak())
        
        # Pages 2-3: Charts
        if self.config.include_charts:
            story.extend(self._create_charts_pages(result))
            story.append(PageBreak())
        
        # Page 4: Metrics
        story.extend(self._create_metrics_page(result))
        story.append(PageBreak())
        
        # Page 5: Warnings
        if self.config.include_warnings:
            story.extend(self._create_warnings_page(result))
            story.append(PageBreak())
        
        # Page 6: Methodology
        if self.config.include_methodology:
            story.extend(self._create_methodology_page())
        
        # Build PDF
        doc.build(story)
        
        buffer.seek(0)
        return buffer.read()
    
    def generate_to_file(
        self,
        result: Any,
        output_path: Union[str, Path],
        product_name: str = "Unnamed Product",
        report_date: Optional[str] = None,
    ) -> None:
        """
        Generate PDF report and save to file.
        
        Args:
            result: DaySimulationResult with simulation data
            output_path: Path to save the PDF
            product_name: Name of the product being analyzed
            report_date: Report date (defaults to today)
        """
        pdf_bytes = self.generate(result, product_name, report_date)
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'wb') as f:
            f.write(pdf_bytes)
    
    # ==========================================================================
    # PAGE BUILDERS
    # ==========================================================================
    
    def _create_executive_summary(
        self,
        result: Any,
        product_name: str,
        report_date: str,
    ) -> List:
        """Create executive summary page."""
        story = []
        
        # Header
        story.append(Paragraph(
            f"{self.config.company_name}",
            self.styles['CustomTitle']
        ))
        story.append(Paragraph(
            self.config.tagline,
            self.styles['Subtitle']
        ))
        story.append(Spacer(1, 20))
        
        # Product info box
        story.append(Paragraph(
            "PROTOCOL ASSESSMENT REPORT",
            self.styles['SectionHeading']
        ))
        
        info_data = [
            ["Product:", product_name],
            ["Report Date:", report_date],
            ["Simulation ID:", getattr(result, 'person_id', 'N/A')],
            ["Status:", "✓ Valid" if getattr(result, 'is_valid', True) else "⚠ Review Required"],
        ]
        
        info_table = Table(info_data, colWidths=[1.5 * inch, 4 * inch])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('TEXTCOLOR', (0, 0), (0, -1), HexColor(self.config.secondary_color)),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 30))
        
        # Key findings
        story.append(Paragraph(
            "KEY FINDINGS",
            self.styles['SectionHeading']
        ))
        
        metrics = getattr(result, 'metrics', {})
        
        findings = [
            f"• <b>Glucose Peak:</b> {format_metric_value('glucose_peak', metrics.get('glucose_peak', 0))} mg/dL",
            f"• <b>Caffeine Peak:</b> {format_metric_value('caffeine_peak', metrics.get('caffeine_peak', 0))} mg/L",
            f"• <b>Alertness Peak:</b> {format_metric_value('alertness_peak', metrics.get('alertness_peak', 0))}%",
            f"• <b>Sleep Disruption Risk:</b> {format_metric_value('risk', metrics.get('sleep_disruption_risk', 0))}",
        ]
        
        for finding in findings:
            story.append(Paragraph(finding, self.styles['BodyText']))
        
        story.append(Spacer(1, 20))
        
        # Summary text
        story.append(Paragraph(
            "SUMMARY",
            self.styles['SectionHeading']
        ))
        
        # Generate summary based on metrics
        summary = self._generate_summary_text(metrics, result)
        story.append(Paragraph(summary, self.styles['BodyText']))
        
        # Warnings preview if any
        warnings = getattr(result, 'warnings', ())
        if warnings:
            story.append(Spacer(1, 15))
            story.append(Paragraph(
                f"⚠ {len(warnings)} warning(s) identified - see Warnings section for details.",
                self.styles['Warning']
            ))
        
        return story
    
    def _create_charts_pages(self, result: Any) -> List:
        """Create pages with 24h response charts."""
        story = []
        
        # Page 2: Individual charts
        story.append(Paragraph(
            "24-HOUR RESPONSE CURVES",
            self.styles['SectionHeading']
        ))
        
        story.append(Paragraph(
            "The following charts show the physiological response over a 24-hour period "
            "based on the simulation model.",
            self.styles['BodyText']
        ))
        story.append(Spacer(1, 10))
        
        time_minutes = np.array(getattr(result, 'time_minutes', np.linspace(0, 1440, 1441)))
        glucose_curve = np.array(getattr(result, 'glucose_curve', np.full(1441, 90)))
        caffeine_curve = np.array(getattr(result, 'caffeine_curve', np.zeros(1441)))
        alertness_curve = np.array(getattr(result, 'alertness_curve', np.full(1441, 50)))
        
        # Glucose chart
        glucose_chart_bytes = create_glucose_chart(time_minutes, glucose_curve)
        glucose_img = Image(io.BytesIO(glucose_chart_bytes), width=6.5 * inch, height=2.5 * inch)
        story.append(glucose_img)
        story.append(Spacer(1, 15))
        
        # Caffeine chart
        caffeine_chart_bytes = create_caffeine_chart(time_minutes, caffeine_curve)
        caffeine_img = Image(io.BytesIO(caffeine_chart_bytes), width=6.5 * inch, height=2.5 * inch)
        story.append(caffeine_img)
        
        story.append(PageBreak())
        
        # Page 3: Alertness and combined
        story.append(Paragraph(
            "24-HOUR RESPONSE CURVES (CONTINUED)",
            self.styles['SectionHeading']
        ))
        
        # Alertness chart
        alertness_chart_bytes = create_alertness_chart(time_minutes, alertness_curve)
        alertness_img = Image(io.BytesIO(alertness_chart_bytes), width=6.5 * inch, height=2.5 * inch)
        story.append(alertness_img)
        story.append(Spacer(1, 20))
        
        # Chart interpretation
        story.append(Paragraph(
            "INTERPRETATION",
            self.styles['SubsectionHeading']
        ))
        
        interpretation = self._generate_chart_interpretation(result)
        story.append(Paragraph(interpretation, self.styles['BodyText']))
        
        return story
    
    def _create_metrics_page(self, result: Any) -> List:
        """Create metrics summary page."""
        story = []
        
        story.append(Paragraph(
            "KEY METRICS ANALYSIS",
            self.styles['SectionHeading']
        ))
        
        story.append(Paragraph(
            "Detailed breakdown of simulation metrics and their interpretation.",
            self.styles['BodyText']
        ))
        story.append(Spacer(1, 15))
        
        metrics = getattr(result, 'metrics', {})
        
        # Metrics summary chart
        if metrics:
            chart_bytes = create_metrics_summary_chart(metrics)
            chart_img = Image(io.BytesIO(chart_bytes), width=6 * inch, height=3.5 * inch)
            story.append(chart_img)
            story.append(Spacer(1, 20))
        
        # Metrics table
        story.append(Paragraph(
            "DETAILED METRICS",
            self.styles['SubsectionHeading']
        ))
        
        # Format metrics for table
        metric_labels = {
            'glucose_peak': 'Glucose Peak',
            'glucose_time_to_peak': 'Time to Peak Glucose',
            'glucose_auc': 'Glucose AUC',
            'glucose_time_above_threshold': 'Time Above Threshold (140 mg/dL)',
            'caffeine_peak': 'Caffeine Peak',
            'caffeine_half_life': 'Caffeine Half-Life',
            'alertness_peak': 'Alertness Peak',
            'alertness_duration_above_threshold': 'Duration Above 60%',
            'sleep_disruption_risk': 'Sleep Disruption Risk',
        }
        
        table_data = [["Metric", "Value", "Unit"]]
        
        units = {
            'glucose_peak': 'mg/dL',
            'glucose_time_to_peak': 'min',
            'glucose_auc': 'mg·min/dL',
            'glucose_time_above_threshold': 'min',
            'caffeine_peak': 'mg/L',
            'caffeine_half_life': 'hours',
            'alertness_peak': '%',
            'alertness_duration_above_threshold': 'min',
            'sleep_disruption_risk': '%',
        }
        
        for key, label in metric_labels.items():
            if key in metrics:
                value = metrics[key]
                unit = units.get(key, '')
                
                # Format value
                if 'risk' in key:
                    formatted_value = f"{value * 100:.1f}"
                elif 'auc' in key:
                    formatted_value = f"{value:.0f}"
                elif 'time' in key or 'duration' in key:
                    formatted_value = f"{value:.0f}"
                else:
                    formatted_value = f"{value:.1f}"
                
                table_data.append([label, formatted_value, unit])
        
        metrics_table = Table(table_data, colWidths=[3.5 * inch, 1.5 * inch, 1 * inch])
        metrics_table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), HexColor(self.config.primary_color)),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            
            # Body
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            
            # Alternating rows
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, HexColor('#F3F4F6')]),
            
            # Borders
            ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
            ('LINEBELOW', (0, 0), (-1, 0), 2, HexColor(self.config.secondary_color)),
            
            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        story.append(metrics_table)
        
        return story
    
    def _create_warnings_page(self, result: Any) -> List:
        """Create warnings and recommendations page."""
        story = []
        
        story.append(Paragraph(
            "WARNINGS & RECOMMENDATIONS",
            self.styles['SectionHeading']
        ))
        
        warnings = getattr(result, 'warnings', ())
        metrics = getattr(result, 'metrics', {})
        
        if not warnings:
            # Generate automatic warnings based on metrics
            warnings = self._generate_automatic_warnings(metrics)
        
        if warnings:
            story.append(Paragraph(
                "The following issues were identified during the simulation:",
                self.styles['BodyText']
            ))
            story.append(Spacer(1, 10))
            
            for i, warning in enumerate(warnings, 1):
                story.append(Paragraph(
                    f"⚠ <b>Warning {i}:</b> {warning}",
                    self.styles['Warning']
                ))
                story.append(Spacer(1, 5))
        else:
            story.append(Paragraph(
                "✓ No significant warnings identified. The simulation results are within "
                "acceptable parameters.",
                self.styles['BodyText']
            ))
        
        story.append(Spacer(1, 30))
        
        # Recommendations
        story.append(Paragraph(
            "GENERAL RECOMMENDATIONS",
            self.styles['SubsectionHeading']
        ))
        
        recommendations = self._generate_recommendations(metrics)
        for rec in recommendations:
            story.append(Paragraph(f"• {rec}", self.styles['BodyText']))
        
        return story
    
    def _create_methodology_page(self) -> List:
        """Create methodology brief page."""
        story = []
        
        story.append(Paragraph(
            "METHODOLOGY",
            self.styles['SectionHeading']
        ))
        
        story.append(Paragraph(
            "<b>Simulation Engine</b>",
            self.styles['SubsectionHeading']
        ))
        
        story.append(Paragraph(
            "This report was generated using the MODULUS metabolic simulation engine, "
            "which integrates validated physiological models to predict 24-hour responses "
            "to supplements and nutrition interventions.",
            self.styles['BodyText']
        ))
        
        story.append(Paragraph(
            "<b>Models Used</b>",
            self.styles['SubsectionHeading']
        ))
        
        models_text = """
        <b>Glucose Metabolism:</b> Based on the Dalla Man et al. (2007) model, a validated 
        12-state ordinary differential equation system that captures glucose-insulin dynamics 
        including gut absorption, hepatic glucose production, and peripheral uptake.<br/><br/>
        
        <b>Caffeine Pharmacokinetics:</b> One-compartment pharmacokinetic model with 
        first-order absorption and elimination. Individual variation modeled via CYP1A2 
        genetic polymorphisms affecting half-life (2.5-10 hours).<br/><br/>
        
        <b>Alertness Score:</b> Derived from adenosine receptor occupancy using an Emax 
        pharmacodynamic model, where caffeine competitively inhibits adenosine binding.
        """
        story.append(Paragraph(models_text, self.styles['BodyText']))
        
        story.append(Paragraph(
            "<b>Limitations</b>",
            self.styles['SubsectionHeading']
        ))
        
        limitations = [
            "Results are based on population-averaged models and individual responses may vary.",
            "The simulation does not account for all possible drug-nutrient interactions.",
            "This report is for informational purposes and does not constitute medical advice.",
            "Validation is ongoing; model predictions should be verified with clinical data.",
        ]
        
        for limitation in limitations:
            story.append(Paragraph(f"• {limitation}", self.styles['BodyText']))
        
        story.append(Spacer(1, 30))
        
        # Footer
        story.append(Paragraph(
            f"Report generated by {self.config.company_name} | {self.config.tagline}",
            self.styles['Footer']
        ))
        story.append(Paragraph(
            "© 2025 MODULUS. All rights reserved.",
            self.styles['Footer']
        ))
        
        return story
    
    # ==========================================================================
    # HELPER METHODS
    # ==========================================================================
    
    def _generate_summary_text(self, metrics: Dict, result: Any) -> str:
        """Generate summary paragraph based on metrics."""
        glucose_peak = metrics.get('glucose_peak', 0)
        caffeine_peak = metrics.get('caffeine_peak', 0)
        sleep_risk = metrics.get('sleep_disruption_risk', 0)
        
        parts = []
        
        # Glucose assessment
        if glucose_peak > 180:
            parts.append("Glucose response shows significant elevation above normal range.")
        elif glucose_peak > 140:
            parts.append("Glucose response shows moderate elevation.")
        else:
            parts.append("Glucose response remains within normal physiological range.")
        
        # Caffeine assessment
        if caffeine_peak > 3.0:
            parts.append("High caffeine exposure detected, which may cause jitter in sensitive individuals.")
        elif caffeine_peak > 1.5:
            parts.append("Moderate caffeine exposure providing sustained alertness.")
        elif caffeine_peak > 0:
            parts.append("Low caffeine exposure with minimal stimulant effect.")
        
        # Sleep risk
        if sleep_risk > 0.3:
            parts.append("Elevated risk of sleep disruption due to late caffeine presence.")
        elif sleep_risk > 0.1:
            parts.append("Moderate sleep risk; consider earlier timing for caffeine-sensitive individuals.")
        
        return " ".join(parts)
    
    def _generate_chart_interpretation(self, result: Any) -> str:
        """Generate interpretation text for charts."""
        metrics = getattr(result, 'metrics', {})
        
        interp = []
        
        glucose_peak = metrics.get('glucose_peak', 0)
        time_to_peak = metrics.get('glucose_time_to_peak', 0)
        
        if time_to_peak > 0:
            interp.append(
                f"Glucose peaked at {glucose_peak:.0f} mg/dL approximately "
                f"{format_duration(time_to_peak)} after intake."
            )
        
        caffeine_hl = metrics.get('caffeine_half_life', 0)
        if caffeine_hl > 0:
            interp.append(
                f"Caffeine elimination half-life was {caffeine_hl:.1f} hours, "
                "indicating normal CYP1A2 metabolism."
            )
        
        alertness_dur = metrics.get('alertness_duration_above_threshold', 0)
        if alertness_dur > 0:
            interp.append(
                f"Alertness remained above the target threshold (60%) for "
                f"{format_duration(alertness_dur)}."
            )
        
        return " ".join(interp) if interp else "Simulation completed successfully."
    
    def _generate_automatic_warnings(self, metrics: Dict) -> List[str]:
        """Generate warnings based on metric thresholds."""
        warnings = []
        
        glucose_peak = metrics.get('glucose_peak', 0)
        if glucose_peak > 180:
            warnings.append(
                f"Glucose peak ({glucose_peak:.0f} mg/dL) exceeds safe threshold (180 mg/dL). "
                "Consider reducing carbohydrate content or glycemic index."
            )
        elif glucose_peak > 160:
            warnings.append(
                f"Glucose peak ({glucose_peak:.0f} mg/dL) is elevated. "
                "Monitor for individuals with insulin resistance."
            )
        
        caffeine_peak = metrics.get('caffeine_peak', 0)
        if caffeine_peak > 4.0:
            warnings.append(
                f"Caffeine level ({caffeine_peak:.1f} mg/L) may cause adverse effects "
                "(jitter, anxiety) in sensitive individuals."
            )
        
        sleep_risk = metrics.get('sleep_disruption_risk', 0)
        if sleep_risk > 0.3:
            warnings.append(
                f"High sleep disruption risk ({sleep_risk*100:.0f}%). "
                "Caffeine intake should occur earlier in the day."
            )
        elif sleep_risk > 0.15:
            warnings.append(
                f"Moderate sleep disruption risk ({sleep_risk*100:.0f}%). "
                "Consider timing recommendations for caffeine-sensitive users."
            )
        
        return warnings
    
    def _generate_recommendations(self, metrics: Dict) -> List[str]:
        """Generate recommendations based on metrics."""
        recommendations = []
        
        sleep_risk = metrics.get('sleep_disruption_risk', 0)
        if sleep_risk > 0.1:
            recommendations.append(
                "Consider adding timing guidance: 'For best results, take before 2 PM.'"
            )
        
        glucose_peak = metrics.get('glucose_peak', 0)
        if glucose_peak > 160:
            recommendations.append(
                "For users with metabolic concerns, recommend taking with fiber or protein "
                "to slow glucose absorption."
            )
        
        caffeine_peak = metrics.get('caffeine_peak', 0)
        if caffeine_peak > 3.0:
            recommendations.append(
                "Consider L-Theanine addition (100mg per 200mg caffeine) to reduce jitter risk."
            )
        
        # General recommendations
        recommendations.append(
            "Include clear dosage instructions and recommended timing on product label."
        )
        recommendations.append(
            "Add warning for caffeine-sensitive individuals if caffeine content exceeds 100mg."
        )
        
        return recommendations
