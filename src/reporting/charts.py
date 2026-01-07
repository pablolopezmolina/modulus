"""
MODULUS Charts Generation Module

Generates matplotlib charts for PDF reports.
All functions return PNG bytes that can be embedded in PDFs.

This module is part of src/reporting/ (CAPA 7 - Output & Delivery).
"""

from typing import Optional, Tuple
import io
import numpy as np

# matplotlib import with non-interactive backend for server use
import matplotlib
matplotlib.use('Agg')  # Must be before importing pyplot
import matplotlib.pyplot as plt
from matplotlib.figure import Figure


# ==============================================================================
# CONFIGURATION
# ==============================================================================

# Chart style configuration
CHART_STYLE = {
    'figure.figsize': (10, 4),
    'figure.dpi': 150,
    'axes.grid': True,
    'axes.grid.which': 'both',
    'grid.alpha': 0.3,
    'lines.linewidth': 2,
    'font.size': 10,
    'axes.labelsize': 11,
    'axes.titlesize': 12,
    'legend.fontsize': 9,
}

# Color palette (professional, colorblind-friendly)
COLORS = {
    'glucose': '#2E86AB',      # Blue
    'insulin': '#A23B72',      # Magenta
    'caffeine': '#F18F01',     # Orange
    'alertness': '#C73E1D',    # Red
    'threshold': '#6B7280',    # Gray
    'safe_zone': '#10B981',    # Green
    'danger_zone': '#EF4444',  # Red
}

# Thresholds for visual markers
THRESHOLDS = {
    'glucose_high': 140,       # mg/dL
    'glucose_very_high': 180,  # mg/dL
    'caffeine_high': 3.0,      # mg/L
    'alertness_low': 50,       # %
}


# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================

def _minutes_to_hours_label(minutes: np.ndarray) -> np.ndarray:
    """Convert minutes array to hour labels for x-axis."""
    return minutes / 60


def _format_time_ticks(ax, time_minutes: np.ndarray) -> None:
    """Format x-axis with time labels (HH:MM format)."""
    # Set ticks every 2 hours
    tick_positions = np.arange(0, 1441, 120)  # Every 2 hours
    tick_labels = [f"{int(m // 60):02d}:00" for m in tick_positions]
    
    ax.set_xticks(tick_positions)
    ax.set_xticklabels(tick_labels, rotation=45, ha='right')
    ax.set_xlim(0, 1440)


def _save_figure_to_bytes(fig: Figure) -> bytes:
    """Save matplotlib figure to PNG bytes."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=150)
    buf.seek(0)
    png_bytes = buf.read()
    buf.close()
    plt.close(fig)
    return png_bytes


# ==============================================================================
# CHART GENERATION FUNCTIONS
# ==============================================================================

def create_glucose_chart(
    time_minutes: np.ndarray,
    glucose_curve: np.ndarray,
    title: str = "Glucose Response (24h)",
    show_thresholds: bool = True,
) -> bytes:
    """
    Create glucose response chart.
    
    Args:
        time_minutes: Time array in minutes (0-1440)
        glucose_curve: Glucose values in mg/dL
        title: Chart title
        show_thresholds: Whether to show threshold lines
        
    Returns:
        PNG bytes of the chart
    """
    with plt.style.context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(10, 4))
        
        # Main glucose line
        ax.plot(
            time_minutes,
            glucose_curve,
            color=COLORS['glucose'],
            linewidth=2,
            label='Glucose'
        )
        
        # Fill under curve
        ax.fill_between(
            time_minutes,
            0,
            glucose_curve,
            color=COLORS['glucose'],
            alpha=0.1
        )
        
        # Threshold lines
        if show_thresholds:
            ax.axhline(
                y=THRESHOLDS['glucose_high'],
                color=COLORS['threshold'],
                linestyle='--',
                linewidth=1,
                label=f"Threshold ({THRESHOLDS['glucose_high']} mg/dL)"
            )
            ax.axhline(
                y=THRESHOLDS['glucose_very_high'],
                color=COLORS['danger_zone'],
                linestyle='--',
                linewidth=1,
                alpha=0.7,
                label=f"High ({THRESHOLDS['glucose_very_high']} mg/dL)"
            )
        
        # Formatting
        ax.set_xlabel('Time of Day')
        ax.set_ylabel('Glucose (mg/dL)')
        ax.set_title(title)
        ax.legend(loc='upper right')
        ax.set_ylim(50, max(200, np.max(glucose_curve) * 1.1))
        _format_time_ticks(ax, time_minutes)
        
        return _save_figure_to_bytes(fig)


def create_caffeine_chart(
    time_minutes: np.ndarray,
    caffeine_curve: np.ndarray,
    title: str = "Caffeine Plasma Concentration (24h)",
    show_thresholds: bool = True,
) -> bytes:
    """
    Create caffeine concentration chart.
    
    Args:
        time_minutes: Time array in minutes (0-1440)
        caffeine_curve: Caffeine values in mg/L
        title: Chart title
        show_thresholds: Whether to show threshold lines
        
    Returns:
        PNG bytes of the chart
    """
    with plt.style.context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(10, 4))
        
        # Main caffeine line
        ax.plot(
            time_minutes,
            caffeine_curve,
            color=COLORS['caffeine'],
            linewidth=2,
            label='Caffeine'
        )
        
        # Fill under curve
        ax.fill_between(
            time_minutes,
            0,
            caffeine_curve,
            color=COLORS['caffeine'],
            alpha=0.1
        )
        
        # Threshold for sleep disruption
        if show_thresholds:
            ax.axhline(
                y=1.0,  # mg/L threshold for sleep issues
                color=COLORS['threshold'],
                linestyle='--',
                linewidth=1,
                label='Sleep Risk Threshold (1.0 mg/L)'
            )
            
            # Mark bedtime zone (22:00-24:00)
            ax.axvspan(
                1320, 1440,  # 22:00 to 24:00
                alpha=0.1,
                color=COLORS['danger_zone'],
                label='Bedtime Zone'
            )
        
        # Formatting
        ax.set_xlabel('Time of Day')
        ax.set_ylabel('Caffeine (mg/L)')
        ax.set_title(title)
        ax.legend(loc='upper right')
        ax.set_ylim(0, max(5, np.max(caffeine_curve) * 1.2))
        _format_time_ticks(ax, time_minutes)
        
        return _save_figure_to_bytes(fig)


def create_alertness_chart(
    time_minutes: np.ndarray,
    alertness_curve: np.ndarray,
    title: str = "Alertness Score (24h)",
    show_thresholds: bool = True,
) -> bytes:
    """
    Create alertness score chart.
    
    Args:
        time_minutes: Time array in minutes (0-1440)
        alertness_curve: Alertness values (0-100)
        title: Chart title
        show_thresholds: Whether to show threshold lines
        
    Returns:
        PNG bytes of the chart
    """
    with plt.style.context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(10, 4))
        
        # Main alertness line
        ax.plot(
            time_minutes,
            alertness_curve,
            color=COLORS['alertness'],
            linewidth=2,
            label='Alertness'
        )
        
        # Fill under curve with gradient effect
        ax.fill_between(
            time_minutes,
            0,
            alertness_curve,
            color=COLORS['alertness'],
            alpha=0.1
        )
        
        # Threshold line
        if show_thresholds:
            ax.axhline(
                y=60,
                color=COLORS['safe_zone'],
                linestyle='--',
                linewidth=1,
                label='Target (60%)'
            )
            ax.axhline(
                y=THRESHOLDS['alertness_low'],
                color=COLORS['threshold'],
                linestyle='--',
                linewidth=1,
                label=f"Low ({THRESHOLDS['alertness_low']}%)"
            )
        
        # Formatting
        ax.set_xlabel('Time of Day')
        ax.set_ylabel('Alertness Score (%)')
        ax.set_title(title)
        ax.legend(loc='upper right')
        ax.set_ylim(0, 100)
        _format_time_ticks(ax, time_minutes)
        
        return _save_figure_to_bytes(fig)


def create_combined_chart(
    time_minutes: np.ndarray,
    glucose_curve: np.ndarray,
    caffeine_curve: np.ndarray,
    alertness_curve: np.ndarray,
    title: str = "Combined 24h Response",
) -> bytes:
    """
    Create combined chart with all three curves.
    Uses dual y-axes for different scales.
    
    Args:
        time_minutes: Time array in minutes (0-1440)
        glucose_curve: Glucose values in mg/dL
        caffeine_curve: Caffeine values in mg/L
        alertness_curve: Alertness values (0-100)
        title: Chart title
        
    Returns:
        PNG bytes of the chart
    """
    with plt.style.context(CHART_STYLE):
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 10), sharex=True)
        
        # Glucose subplot
        ax1.plot(
            time_minutes,
            glucose_curve,
            color=COLORS['glucose'],
            linewidth=2,
            label='Glucose'
        )
        ax1.fill_between(time_minutes, 0, glucose_curve, color=COLORS['glucose'], alpha=0.1)
        ax1.axhline(y=140, color=COLORS['threshold'], linestyle='--', linewidth=1, alpha=0.7)
        ax1.set_ylabel('Glucose (mg/dL)')
        ax1.set_ylim(50, 200)
        ax1.legend(loc='upper right')
        ax1.grid(True, alpha=0.3)
        
        # Caffeine subplot
        ax2.plot(
            time_minutes,
            caffeine_curve,
            color=COLORS['caffeine'],
            linewidth=2,
            label='Caffeine'
        )
        ax2.fill_between(time_minutes, 0, caffeine_curve, color=COLORS['caffeine'], alpha=0.1)
        ax2.axhline(y=1.0, color=COLORS['threshold'], linestyle='--', linewidth=1, alpha=0.7)
        ax2.set_ylabel('Caffeine (mg/L)')
        ax2.set_ylim(0, 5)
        ax2.legend(loc='upper right')
        ax2.grid(True, alpha=0.3)
        
        # Alertness subplot
        ax3.plot(
            time_minutes,
            alertness_curve,
            color=COLORS['alertness'],
            linewidth=2,
            label='Alertness'
        )
        ax3.fill_between(time_minutes, 0, alertness_curve, color=COLORS['alertness'], alpha=0.1)
        ax3.axhline(y=60, color=COLORS['safe_zone'], linestyle='--', linewidth=1, alpha=0.7)
        ax3.set_ylabel('Alertness (%)')
        ax3.set_ylim(0, 100)
        ax3.legend(loc='upper right')
        ax3.grid(True, alpha=0.3)
        
        # X-axis formatting on bottom subplot
        _format_time_ticks(ax3, time_minutes)
        ax3.set_xlabel('Time of Day')
        
        # Overall title
        fig.suptitle(title, fontsize=14, fontweight='bold')
        fig.tight_layout()
        
        return _save_figure_to_bytes(fig)


def create_metrics_summary_chart(
    metrics: dict,
    title: str = "Key Metrics Summary",
) -> bytes:
    """
    Create a bar chart summarizing key metrics.
    
    Args:
        metrics: Dictionary of metric names to values
        title: Chart title
        
    Returns:
        PNG bytes of the chart
    """
    with plt.style.context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(10, 5))
        
        # Normalize metrics for display
        display_metrics = {
            'Glucose Peak\n(mg/dL)': metrics.get('glucose_peak', 0),
            'Caffeine Peak\n(mg/L)': metrics.get('caffeine_peak', 0) * 50,  # Scale for visibility
            'Alertness Peak\n(%)': metrics.get('alertness_peak', 0),
            'Sleep Risk\n(%)': metrics.get('sleep_disruption_risk', 0) * 100,
        }
        
        names = list(display_metrics.keys())
        values = list(display_metrics.values())
        
        colors = [
            COLORS['glucose'],
            COLORS['caffeine'],
            COLORS['alertness'],
            COLORS['danger_zone'] if values[3] > 25 else COLORS['safe_zone'],
        ]
        
        bars = ax.bar(names, values, color=colors, alpha=0.8, edgecolor='black')
        
        # Add value labels on bars
        for bar, val, name in zip(bars, values, names):
            # Adjust label for caffeine (was scaled)
            if 'Caffeine' in name:
                label = f"{val/50:.1f}"
            elif 'Sleep' in name:
                label = f"{val:.0f}%"
            else:
                label = f"{val:.0f}"
            
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 2,
                label,
                ha='center',
                va='bottom',
                fontsize=11,
                fontweight='bold'
            )
        
        ax.set_ylabel('Value')
        ax.set_title(title)
        ax.set_ylim(0, max(values) * 1.15)
        
        return _save_figure_to_bytes(fig)
