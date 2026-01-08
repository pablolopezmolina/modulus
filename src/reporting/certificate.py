"""
Modulus Protocol Certificate Generator.

Session 10.3: Generate professional 1-page PDF certificates with
"MODULUS PROTOCOL VERIFIED" branding, decision verdicts, and key metrics.

This module creates certificates that can be:
- Printed and displayed
- Included in Pack 2 deliverables
- Verified via QR code (optional)

Example:
    >>> from certificate import CertificateGenerator
    >>> gen = CertificateGenerator()
    >>> result = gen.generate(population_results, decision, product_name="Energy Pro Max")
    >>> print(result.certificate_id)  # MODULUS-2025-ABC123
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import json
import hashlib
import secrets

# reportlab imports for PDF generation
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import inch, mm
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, KeepTogether, PageBreak
)
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.graphics import renderPDF


# ============================================================================
# CONSTANTS
# ============================================================================

# Colors for different verdicts
VERDICT_COLORS = {
    "GO": HexColor("#22c55e"),       # Green
    "CAUTION": HexColor("#f59e0b"),  # Amber/Orange
    "NO_GO": HexColor("#ef4444"),    # Red
}

# Background colors (lighter versions)
VERDICT_BG_COLORS = {
    "GO": HexColor("#dcfce7"),       # Light green
    "CAUTION": HexColor("#fef3c7"),  # Light amber
    "NO_GO": HexColor("#fee2e2"),    # Light red
}

# Corporate colors
MODULUS_BLUE = HexColor("#1e40af")
MODULUS_DARK = HexColor("#1e293b")
MODULUS_LIGHT = HexColor("#f8fafc")
MODULUS_GRAY = HexColor("#64748b")

# Key metrics to display on certificate (in order)
KEY_METRICS_DISPLAY = [
    ("alertness_peak", "Peak Alertness", "%"),
    ("alertness_duration_above_60", "Duration >60%", "min"),
    ("glucose_peak", "Peak Glucose", "mg/dL"),
    ("caffeine_half_life", "Caffeine Half-Life", "h"),
]

# Key risks to display (in order of importance)
KEY_RISKS_DISPLAY = [
    "sleep_disruption",
    "jitter",
    "hyperglycemia",
    "crash",
    "severe_hyperglycemia",
]


# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class CertificateConfig:
    """Configuration for certificate generation.
    
    Attributes:
        company_name: Company name in header (default: "MODULUS")
        include_qr_code: Whether to include QR code for verification
        qr_base_url: Base URL for verification links
        page_size: PDF page size (default: A4)
        show_top_n_risks: Number of top risks to display
        show_top_n_metrics: Number of key metrics to display
    """
    company_name: str = "MODULUS"
    include_qr_code: bool = True
    qr_base_url: str = "https://verify.modulus.bio/cert/"
    page_size: Tuple[float, float] = A4
    show_top_n_risks: int = 4
    show_top_n_metrics: int = 4


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass(frozen=True)
class CertificateInfo:
    """Immutable certificate information.
    
    Contains all data needed to render a certificate.
    
    Attributes:
        certificate_id: Unique ID (MODULUS-YYYY-XXXXXX format)
        product_name: Name of the assessed product
        verdict: Decision verdict ("GO", "CAUTION", "NO_GO")
        confidence: Decision confidence (0-1)
        issue_date: When the certificate was issued
        n_individuals: Number of simulated individuals
        n_valid: Number of valid simulations
        key_metrics: Dict of metric name -> mean value
        top_risks: List of (risk_name, percentage) tuples
        summary: Brief summary text
        version: MODULUS version used
    """
    certificate_id: str
    product_name: str
    verdict: str
    confidence: float
    issue_date: datetime
    n_individuals: int
    n_valid: int
    key_metrics: Dict[str, float]
    top_risks: List[Tuple[str, float]]
    summary: str
    version: str = "3.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "certificate_id": self.certificate_id,
            "product_name": self.product_name,
            "verdict": self.verdict,
            "confidence": self.confidence,
            "issue_date": self.issue_date.isoformat(),
            "n_individuals": self.n_individuals,
            "n_valid": self.n_valid,
            "key_metrics": self.key_metrics,
            "top_risks": self.top_risks,
            "summary": self.summary,
            "version": self.version,
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class CertificateResult:
    """Result of certificate generation.
    
    Attributes:
        certificate_id: The unique certificate ID
        output_path: Path to the generated PDF file
        info: The CertificateInfo used to generate the certificate
        verification_url: URL for online verification (if QR enabled)
    """
    certificate_id: str
    output_path: str
    info: CertificateInfo
    verification_url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "certificate_id": self.certificate_id,
            "output_path": self.output_path,
            "info": self.info.to_dict(),
            "verification_url": self.verification_url,
        }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def generate_certificate_id(seed: Optional[int] = None) -> str:
    """Generate a unique certificate ID.
    
    Format: MODULUS-YYYY-XXXXXX where XXXXXX is a random hex string.
    
    Args:
        seed: Optional seed for deterministic ID generation
        
    Returns:
        Certificate ID string
    """
    year = datetime.now().year
    
    if seed is not None:
        # Deterministic generation
        import random
        rng = random.Random(seed)
        hex_part = ''.join(rng.choices('0123456789ABCDEF', k=6))
    else:
        # Random generation
        hex_part = secrets.token_hex(3).upper()
    
    return f"MODULUS-{year}-{hex_part}"


def _format_metric_name(metric_id: str) -> str:
    """Format metric ID for display."""
    # Lookup in KEY_METRICS_DISPLAY
    for mid, display_name, _ in KEY_METRICS_DISPLAY:
        if mid == metric_id:
            return display_name
    
    # Fallback: convert snake_case to Title Case
    return metric_id.replace("_", " ").title()


def _format_risk_name(risk_id: str) -> str:
    """Format risk ID for display."""
    names = {
        "sleep_disruption": "Sleep Disruption",
        "jitter": "Jitter Risk",
        "hyperglycemia": "Hyperglycemia",
        "severe_hyperglycemia": "Severe Hyperglycemia",
        "hypoglycemia": "Hypoglycemia",
        "crash": "Energy Crash",
    }
    return names.get(risk_id, risk_id.replace("_", " ").title())


def _format_metric_value(metric_id: str, value: float) -> str:
    """Format metric value with appropriate unit."""
    for mid, _, unit in KEY_METRICS_DISPLAY:
        if mid == metric_id:
            if unit == "%":
                return f"{value:.1f}%"
            elif unit == "min":
                return f"{value:.0f} min"
            elif unit == "mg/dL":
                return f"{value:.1f} mg/dL"
            elif unit == "h":
                return f"{value:.1f} h"
    return f"{value:.2f}"


# ============================================================================
# CERTIFICATE GENERATOR
# ============================================================================

class CertificateGenerator:
    """Generates Modulus Protocol Verification Certificates.
    
    Creates professional 1-page PDF certificates with:
    - "MODULUS PROTOCOL VERIFIED" branding
    - Product name and verdict (GO/CAUTION/NO_GO)
    - Key metrics summary
    - Top risks identified
    - Date and unique certificate ID
    - QR code for verification (optional)
    
    Example:
        >>> gen = CertificateGenerator()
        >>> result = gen.generate(results, decision, product_name="Energy Pro")
        >>> print(f"Certificate: {result.certificate_id}")
        >>> print(f"PDF saved to: {result.output_path}")
    """
    
    def __init__(self, config: Optional[CertificateConfig] = None):
        """Initialize the certificate generator.
        
        Args:
            config: Optional configuration. Uses defaults if not provided.
        """
        self.config = config or CertificateConfig()
        self._styles = self._create_styles()
    
    def _create_styles(self) -> Dict[str, ParagraphStyle]:
        """Create custom paragraph styles for the certificate."""
        base_styles = getSampleStyleSheet()
        
        styles = {
            "title": ParagraphStyle(
                "CertTitle",
                parent=base_styles["Title"],
                fontSize=28,
                textColor=MODULUS_DARK,
                alignment=TA_CENTER,
                spaceAfter=6,
            ),
            "subtitle": ParagraphStyle(
                "CertSubtitle",
                parent=base_styles["Normal"],
                fontSize=14,
                textColor=MODULUS_GRAY,
                alignment=TA_CENTER,
                spaceAfter=20,
            ),
            "product_name": ParagraphStyle(
                "ProductName",
                parent=base_styles["Heading1"],
                fontSize=20,
                textColor=MODULUS_DARK,
                alignment=TA_CENTER,
                spaceBefore=10,
                spaceAfter=15,
            ),
            "verdict": ParagraphStyle(
                "Verdict",
                parent=base_styles["Heading1"],
                fontSize=36,
                alignment=TA_CENTER,
                spaceBefore=10,
                spaceAfter=10,
            ),
            "section_header": ParagraphStyle(
                "SectionHeader",
                parent=base_styles["Heading2"],
                fontSize=12,
                textColor=MODULUS_DARK,
                spaceBefore=15,
                spaceAfter=8,
            ),
            "body": ParagraphStyle(
                "CertBody",
                parent=base_styles["Normal"],
                fontSize=10,
                textColor=MODULUS_DARK,
                alignment=TA_LEFT,
            ),
            "footer": ParagraphStyle(
                "Footer",
                parent=base_styles["Normal"],
                fontSize=8,
                textColor=MODULUS_GRAY,
                alignment=TA_CENTER,
            ),
            "metric_label": ParagraphStyle(
                "MetricLabel",
                parent=base_styles["Normal"],
                fontSize=9,
                textColor=MODULUS_GRAY,
            ),
            "metric_value": ParagraphStyle(
                "MetricValue",
                parent=base_styles["Normal"],
                fontSize=11,
                textColor=MODULUS_DARK,
            ),
        }
        
        return styles
    
    def prepare(
        self,
        results: Any,  # PopulationSimulationResult
        decision: Any,  # Decision
        product_name: Optional[str] = None,
        certificate_id: Optional[str] = None,
        seed: Optional[int] = None,
    ) -> CertificateInfo:
        """Prepare certificate information from simulation results.
        
        Args:
            results: PopulationSimulationResult from simulation
            decision: Decision from DecisionEngine
            product_name: Optional product name (uses formulation.name if not provided)
            certificate_id: Optional pre-generated certificate ID
            seed: Optional seed for deterministic ID generation
            
        Returns:
            CertificateInfo with all data needed for rendering
        """
        # Determine product name
        if product_name:
            final_product_name = product_name
        elif hasattr(results, 'formulation') and results.formulation is not None:
            final_product_name = results.formulation.name
        else:
            final_product_name = "Unknown Product"
        
        # Generate certificate ID
        if certificate_id:
            cert_id = certificate_id
        else:
            cert_id = generate_certificate_id(seed=seed)
        
        # Extract key metrics
        key_metrics = {}
        metrics_stats = getattr(results, 'metrics_stats', {})
        
        for metric_id, _, _ in KEY_METRICS_DISPLAY[:self.config.show_top_n_metrics]:
            if metric_id in metrics_stats:
                key_metrics[metric_id] = metrics_stats[metric_id].get("mean", 0.0)
        
        # Extract top risks
        risk_analysis = getattr(results, 'risk_analysis', {})
        top_risks: List[Tuple[str, float]] = []
        
        # Get risks from decision if available
        if hasattr(decision, 'top_risks') and decision.top_risks:
            for risk in decision.top_risks[:self.config.show_top_n_risks]:
                if isinstance(risk, dict):
                    risk_id = risk.get("risk_id", "unknown")
                    risk_pct = risk.get("percentage", 0.0)
                else:
                    risk_id = getattr(risk, 'risk_id', 'unknown')
                    risk_pct = getattr(risk, 'percentage', 0.0)
                top_risks.append((risk_id, risk_pct))
        
        # Fallback to risk_analysis if no top_risks in decision
        if not top_risks and risk_analysis:
            sorted_risks = sorted(
                risk_analysis.items(),
                key=lambda x: x[1],
                reverse=True
            )
            top_risks = sorted_risks[:self.config.show_top_n_risks]
        
        # Get summary
        summary = getattr(decision, 'summary', 'Assessment complete.')
        
        return CertificateInfo(
            certificate_id=cert_id,
            product_name=final_product_name,
            verdict=decision.verdict,
            confidence=decision.confidence,
            issue_date=datetime.now(),
            n_individuals=getattr(results, 'n_individuals', 0),
            n_valid=getattr(results, 'n_valid', 0),
            key_metrics=key_metrics,
            top_risks=top_risks,
            summary=summary,
        )
    
    def _get_verification_url(self, certificate_id: str) -> str:
        """Generate verification URL for QR code."""
        return f"{self.config.qr_base_url}{certificate_id}"
    
    def _create_qr_code_image(self, url: str, size: float = 60) -> Optional[Drawing]:
        """Create a simple QR code placeholder.
        
        Note: For production, use qrcode library. This creates a placeholder.
        """
        try:
            # Try to use qrcode library if available
            import qrcode
            from io import BytesIO
            
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=2,
            )
            qr.add_data(url)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Save to BytesIO and return as reportlab Image
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            
            return Image(buffer, width=size, height=size)
            
        except ImportError:
            # Fallback: create a placeholder drawing
            d = Drawing(size, size)
            d.add(Rect(0, 0, size, size, fillColor=white, strokeColor=black))
            d.add(String(
                size/2, size/2, "QR",
                fontSize=12,
                fillColor=MODULUS_GRAY,
                textAnchor='middle'
            ))
            return d
    
    def generate(
        self,
        results: Any,  # PopulationSimulationResult
        decision: Any,  # Decision
        product_name: Optional[str] = None,
        output_path: Optional[str] = None,
        seed: Optional[int] = None,
    ) -> CertificateResult:
        """Generate a certificate PDF.
        
        Args:
            results: PopulationSimulationResult from simulation
            decision: Decision from DecisionEngine
            product_name: Optional product name
            output_path: Optional output file path (auto-generated if not provided)
            seed: Optional seed for deterministic certificate ID
            
        Returns:
            CertificateResult with certificate ID and file path
        """
        # Prepare certificate info
        info = self.prepare(
            results=results,
            decision=decision,
            product_name=product_name,
            seed=seed,
        )
        
        # Determine output path
        if output_path is None:
            output_path = f"certificate_{info.certificate_id}.pdf"
        
        # Create parent directories if needed
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Generate verification URL
        verification_url = None
        if self.config.include_qr_code:
            verification_url = self._get_verification_url(info.certificate_id)
        
        # Build PDF
        self._build_pdf(info, output_path, verification_url)
        
        return CertificateResult(
            certificate_id=info.certificate_id,
            output_path=output_path,
            info=info,
            verification_url=verification_url,
        )
    
    def _build_pdf(
        self,
        info: CertificateInfo,
        output_path: str,
        verification_url: Optional[str],
    ) -> None:
        """Build the PDF document."""
        # Create document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=self.config.page_size,
            leftMargin=0.75*inch,
            rightMargin=0.75*inch,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch,
        )
        
        # Build story (content)
        story = []
        
        # Header with border
        story.append(self._create_header())
        story.append(Spacer(1, 15))
        
        # Certificate title
        story.append(Paragraph(
            "MODULUS PROTOCOL",
            self._styles["title"]
        ))
        story.append(Paragraph(
            "VERIFICATION CERTIFICATE",
            self._styles["subtitle"]
        ))
        
        # Product name
        story.append(Paragraph(
            f'"{info.product_name}"',
            self._styles["product_name"]
        ))
        
        # Verdict with colored background
        verdict_table = self._create_verdict_section(info)
        story.append(verdict_table)
        story.append(Spacer(1, 15))
        
        # Key metrics section
        story.append(Paragraph("KEY METRICS", self._styles["section_header"]))
        metrics_table = self._create_metrics_table(info)
        story.append(metrics_table)
        story.append(Spacer(1, 10))
        
        # Risk summary section
        if info.top_risks:
            story.append(Paragraph("RISK ANALYSIS", self._styles["section_header"]))
            risks_table = self._create_risks_table(info)
            story.append(risks_table)
            story.append(Spacer(1, 10))
        
        # Summary
        story.append(Paragraph("SUMMARY", self._styles["section_header"]))
        story.append(Paragraph(info.summary, self._styles["body"]))
        story.append(Spacer(1, 20))
        
        # Footer with certificate ID, date, and QR code
        footer_table = self._create_footer(info, verification_url)
        story.append(footer_table)
        
        # Build the PDF
        doc.build(story)
    
    def _create_header(self) -> Table:
        """Create the certificate header."""
        header_data = [[
            Paragraph(
                f"<b>{self.config.company_name}</b>",
                ParagraphStyle(
                    "HeaderText",
                    fontSize=14,
                    textColor=MODULUS_BLUE,
                    alignment=TA_LEFT,
                )
            )
        ]]
        
        header_table = Table(header_data, colWidths=[6.5*inch])
        header_table.setStyle(TableStyle([
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('LINEBELOW', (0, 0), (-1, 0), 2, MODULUS_BLUE),
        ]))
        
        return header_table
    
    def _create_verdict_section(self, info: CertificateInfo) -> Table:
        """Create the verdict display section."""
        verdict_color = VERDICT_COLORS.get(info.verdict, MODULUS_DARK)
        bg_color = VERDICT_BG_COLORS.get(info.verdict, MODULUS_LIGHT)
        
        verdict_style = ParagraphStyle(
            "VerdictDisplay",
            fontSize=36,
            textColor=verdict_color,
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
        )
        
        confidence_style = ParagraphStyle(
            "ConfidenceDisplay",
            fontSize=12,
            textColor=MODULUS_GRAY,
            alignment=TA_CENTER,
        )
        
        verdict_text = info.verdict.replace("_", " ")
        confidence_text = f"Confidence: {info.confidence*100:.0f}%"
        
        data = [[
            Paragraph(f"<b>{verdict_text}</b>", verdict_style)
        ], [
            Paragraph(confidence_text, confidence_style)
        ]]
        
        table = Table(data, colWidths=[4*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), bg_color),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, 0), 15),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 15),
            ('LEFTPADDING', (0, 0), (-1, -1), 20),
            ('RIGHTPADDING', (0, 0), (-1, -1), 20),
            ('BOX', (0, 0), (-1, -1), 2, verdict_color),
        ]))
        
        # Wrap in another table for centering
        wrapper = Table([[table]], colWidths=[6.5*inch])
        wrapper.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ]))
        
        return wrapper
    
    def _create_metrics_table(self, info: CertificateInfo) -> Table:
        """Create the key metrics display table."""
        if not info.key_metrics:
            # Empty state
            return Paragraph(
                "No metrics available",
                self._styles["body"]
            )
        
        # Create metric cells
        metric_cells = []
        for metric_id, value in info.key_metrics.items():
            label = _format_metric_name(metric_id)
            formatted_value = _format_metric_value(metric_id, value)
            
            cell_content = [
                Paragraph(formatted_value, self._styles["metric_value"]),
                Paragraph(label, self._styles["metric_label"]),
            ]
            metric_cells.append(cell_content)
        
        # Pad to 4 cells for consistent layout
        while len(metric_cells) < 4:
            metric_cells.append(["", ""])
        
        # Create table with 4 columns
        data = [
            metric_cells[:4] if len(metric_cells) >= 4 else metric_cells
        ]
        
        # Flatten: each cell is a mini-table
        row_data = []
        for cell in metric_cells[:4]:
            if cell and cell[0]:
                mini_table = Table([[cell[0]], [cell[1]]], colWidths=[1.5*inch])
                mini_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING', (0, 0), (-1, -1), 5),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ]))
                row_data.append(mini_table)
            else:
                row_data.append("")
        
        table = Table([row_data], colWidths=[1.625*inch]*4)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), MODULUS_LIGHT),
            ('BOX', (0, 0), (-1, -1), 1, MODULUS_GRAY),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, MODULUS_GRAY),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        
        return table
    
    def _create_risks_table(self, info: CertificateInfo) -> Table:
        """Create the risk analysis table."""
        if not info.top_risks:
            return Paragraph("No significant risks identified", self._styles["body"])
        
        # Header row
        data = [["Risk", "Population %", "Status"]]
        
        for risk_id, percentage in info.top_risks:
            risk_name = _format_risk_name(risk_id)
            pct_str = f"{percentage:.1f}%"
            
            # Status based on percentage
            if percentage < 10:
                status = "✓ Low"
            elif percentage < 25:
                status = "⚠ Moderate"
            else:
                status = "✗ High"
            
            data.append([risk_name, pct_str, status])
        
        table = Table(data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
        table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), MODULUS_DARK),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            
            # Body
            ('BACKGROUND', (0, 1), (-1, -1), white),
            ('TEXTCOLOR', (0, 1), (-1, -1), MODULUS_DARK),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, MODULUS_GRAY),
            
            # Alignment
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        return table
    
    def _create_footer(
        self,
        info: CertificateInfo,
        verification_url: Optional[str],
    ) -> Table:
        """Create the certificate footer with ID, date, and optional QR."""
        date_str = info.issue_date.strftime("%Y-%m-%d %H:%M UTC")
        
        footer_left = [
            Paragraph(f"<b>Certificate ID:</b> {info.certificate_id}", self._styles["footer"]),
            Paragraph(f"<b>Issue Date:</b> {date_str}", self._styles["footer"]),
            Paragraph(f"<b>Population:</b> {info.n_valid:,}/{info.n_individuals:,} valid", self._styles["footer"]),
            Paragraph(f"<b>Version:</b> MODULUS v{info.version}", self._styles["footer"]),
        ]
        
        # Left column: certificate info
        left_table = Table([[p] for p in footer_left], colWidths=[4*inch])
        left_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        
        # Right column: QR code or empty
        if self.config.include_qr_code and verification_url:
            qr_image = self._create_qr_code_image(verification_url, size=70)
            qr_label = Paragraph(
                "Scan to verify",
                ParagraphStyle("QRLabel", fontSize=7, textColor=MODULUS_GRAY, alignment=TA_CENTER)
            )
            right_content = Table([[qr_image], [qr_label]], colWidths=[1.5*inch])
            right_content.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ]))
        else:
            right_content = ""
        
        # Combine
        footer_table = Table(
            [[left_table, right_content]],
            colWidths=[4.5*inch, 2*inch]
        )
        footer_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LINEABOVE', (0, 0), (-1, 0), 1, MODULUS_GRAY),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
        ]))
        
        return footer_table


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def generate_certificate(
    results: Any,
    decision: Any,
    product_name: Optional[str] = None,
    output_path: Optional[str] = None,
    config: Optional[CertificateConfig] = None,
    seed: Optional[int] = None,
) -> CertificateResult:
    """Generate a Modulus Protocol certificate.
    
    Convenience function that creates a generator and produces a certificate.
    
    Args:
        results: PopulationSimulationResult
        decision: Decision from DecisionEngine
        product_name: Optional product name
        output_path: Optional output path
        config: Optional configuration
        seed: Optional seed for deterministic ID
        
    Returns:
        CertificateResult with file path and certificate info
    """
    gen = CertificateGenerator(config=config)
    return gen.generate(
        results=results,
        decision=decision,
        product_name=product_name,
        output_path=output_path,
        seed=seed,
    )


def format_certificate_for_pdf(info: CertificateInfo) -> Dict[str, Any]:
    """Format certificate info for PDF v2 integration.
    
    Returns a dictionary with pre-formatted content ready for
    embedding in the main MODULUS PDF report.
    
    Args:
        info: CertificateInfo to format
        
    Returns:
        Dictionary with formatted tables and text
    """
    # Metrics table data
    metrics_table = []
    for metric_id, value in info.key_metrics.items():
        metrics_table.append({
            "metric": _format_metric_name(metric_id),
            "value": _format_metric_value(metric_id, value),
        })
    
    # Risks table data
    risks_table = []
    for risk_id, percentage in info.top_risks:
        if percentage < 10:
            status = "Low"
        elif percentage < 25:
            status = "Moderate"
        else:
            status = "High"
        
        risks_table.append({
            "risk": _format_risk_name(risk_id),
            "percentage": f"{percentage:.1f}%",
            "status": status,
        })
    
    return {
        "title": "MODULUS PROTOCOL VERIFICATION CERTIFICATE",
        "certificate_id": info.certificate_id,
        "product_name": info.product_name,
        "verdict": info.verdict,
        "confidence": f"{info.confidence*100:.0f}%",
        "issue_date": info.issue_date.strftime("%Y-%m-%d"),
        "population": f"{info.n_valid:,}/{info.n_individuals:,}",
        "summary": info.summary,
        "metrics_table": metrics_table,
        "risks_table": risks_table,
        "version": info.version,
    }


# ============================================================================
# MODULE EXPORTS
# ============================================================================

__all__ = [
    # Configuration
    "CertificateConfig",
    
    # Data classes
    "CertificateInfo",
    "CertificateResult",
    
    # Main class
    "CertificateGenerator",
    
    # Convenience functions
    "generate_certificate",
    "generate_certificate_id",
    "format_certificate_for_pdf",
]
