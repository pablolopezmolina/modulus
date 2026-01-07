"""
Chart generation for PDF reports.

Sesión 7.1: PDF v1 Completo
Creates matplotlib charts for embedding in PDF reports.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple
import numpy as np
import io

# Matplotlib with non-interactive backend for PDF generation
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.colors import LinearSegmentedColormap


@dataclass
class ChartMetadata:
    """Metadata about a generated chart."""
    x_label: str
    y_label: str
    title: str
    width_inches: float
    height_inches: float


class ChartGenerator:
    """Generates charts for MODULUS PDF reports."""
    
    COLORS = {
        "primary": "#2E86AB",
        "secondary": "#A23B72",
        "success": "#00AA00",
        "warning": "#FFA500",
        "danger": "#AA0000",
        "neutral": "#6C757D",
        "band_fill": "#2E86AB",
    }
    
    def __init__(self, dpi: int = 150, figsize: Tuple[float, float] = (8, 4)):
        self.dpi = dpi
        self.figsize = figsize
        self._setup_style()
    
    def _setup_style(self):
        plt.rcParams.update({
            'font.family': 'sans-serif',
            'font.size': 10,
            'axes.spines.top': False,
            'axes.spines.right': False,
            'axes.grid': True,
            'grid.alpha': 0.3,
        })
    
    def _minutes_to_hours(self, minutes: np.ndarray) -> np.ndarray:
        return minutes / 60.0
    
    def _format_hour_labels(self, ax, max_hours: float = 24):
        ax.set_xlim(0, max_hours)
        ax.set_xticks([0, 4, 8, 12, 16, 20, 24])
        ax.set_xticklabels(['00:00', '04:00', '08:00', '12:00', '16:00', '20:00', '24:00'])
    
    def _fig_to_bytes(self, fig: Figure) -> bytes:
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=self.dpi, bbox_inches='tight', facecolor='white')
        buf.seek(0)
        data = buf.read()
        buf.close()
        plt.close(fig)
        return data
    
    def create_glucose_chart(self, time_minutes: np.ndarray, percentiles: Dict[str, np.ndarray], return_metadata: bool = False) -> Any:
        fig, ax = plt.subplots(figsize=self.figsize)
        hours = self._minutes_to_hours(time_minutes)
        
        ax.fill_between(hours, percentiles["p5"], percentiles["p95"], alpha=0.15, color=self.COLORS["band_fill"])
        ax.fill_between(hours, percentiles["p25"], percentiles["p75"], alpha=0.25, color=self.COLORS["band_fill"])
        ax.plot(hours, percentiles["p50"], color=self.COLORS["primary"], linewidth=2, label='Median')
        ax.axhline(y=140, color=self.COLORS["warning"], linestyle='--', alpha=0.7)
        
        ax.set_xlabel('Time of Day (hours)')
        ax.set_ylabel('Plasma Glucose (mg/dL)')
        ax.set_title('24-Hour Glucose Response')
        self._format_hour_labels(ax)
        ax.set_ylim(50, 200)
        
        if return_metadata:
            plt.close(fig)
            return ChartMetadata(x_label='Time of Day (hours)', y_label='Plasma Glucose (mg/dL)', title='24-Hour Glucose', width_inches=self.figsize[0], height_inches=self.figsize[1])
        return self._fig_to_bytes(fig)
    
    def create_caffeine_chart(self, time_minutes: np.ndarray, percentiles: Dict[str, np.ndarray], return_metadata: bool = False) -> Any:
        fig, ax = plt.subplots(figsize=self.figsize)
        hours = self._minutes_to_hours(time_minutes)
        
        ax.fill_between(hours, percentiles["p5"], percentiles["p95"], alpha=0.15, color=self.COLORS["secondary"])
        ax.fill_between(hours, percentiles["p25"], percentiles["p75"], alpha=0.25, color=self.COLORS["secondary"])
        ax.plot(hours, percentiles["p50"], color=self.COLORS["secondary"], linewidth=2)
        ax.axhline(y=4.0, color=self.COLORS["warning"], linestyle='--', alpha=0.7)
        ax.axhline(y=1.0, color=self.COLORS["neutral"], linestyle='--', alpha=0.7)
        
        ax.set_xlabel('Time of Day (hours)')
        ax.set_ylabel('Plasma Caffeine (mg/L)')
        ax.set_title('24-Hour Caffeine Concentration')
        self._format_hour_labels(ax)
        
        if return_metadata:
            plt.close(fig)
            return ChartMetadata(x_label='Time (hours)', y_label='Caffeine (mg/L)', title='Caffeine', width_inches=self.figsize[0], height_inches=self.figsize[1])
        return self._fig_to_bytes(fig)
    
    def create_alertness_chart(self, time_minutes: np.ndarray, percentiles: Dict[str, np.ndarray], return_metadata: bool = False) -> Any:
        fig, ax = plt.subplots(figsize=self.figsize)
        hours = self._minutes_to_hours(time_minutes)
        
        ax.fill_between(hours, percentiles["p5"], percentiles["p95"], alpha=0.15, color=self.COLORS["success"])
        ax.fill_between(hours, percentiles["p25"], percentiles["p75"], alpha=0.25, color=self.COLORS["success"])
        ax.plot(hours, percentiles["p50"], color=self.COLORS["success"], linewidth=2)
        ax.axhline(y=60, color=self.COLORS["neutral"], linestyle='--', alpha=0.7)
        
        ax.set_xlabel('Time of Day (hours)')
        ax.set_ylabel('Alertness Score (%)')
        ax.set_title('24-Hour Alertness Profile')
        self._format_hour_labels(ax)
        ax.set_ylim(0, 100)
        
        if return_metadata:
            plt.close(fig)
            return ChartMetadata(x_label='Time (hours)', y_label='Alertness (%)', title='Alertness', width_inches=self.figsize[0], height_inches=self.figsize[1])
        return self._fig_to_bytes(fig)
    
    def create_risk_heatmap(self, risk_map: Any, return_metadata: bool = False) -> Any:
        matrices = risk_map.matrices if hasattr(risk_map, 'matrices') else risk_map
        
        if not matrices:
            fig, ax = plt.subplots(figsize=(6, 4))
            ax.text(0.5, 0.5, 'No risk data', ha='center', va='center')
            ax.axis('off')
            if return_metadata:
                plt.close(fig)
                return ChartMetadata(x_label='', y_label='', title='Risk Heatmap', width_inches=6, height_inches=4)
            return self._fig_to_bytes(fig)
        
        dimension = list(matrices.keys())[0]
        data = matrices[dimension]
        segments = list(data.keys())
        risks = list(data[segments[0]].keys()) if segments else []
        
        matrix = np.array([[data[seg].get(r, 0) for r in risks] for seg in segments])
        
        fig, ax = plt.subplots(figsize=(8, 5))
        cmap = LinearSegmentedColormap.from_list('risk', ['#00AA00', '#FFFF00', '#AA0000'])
        im = ax.imshow(matrix, cmap=cmap, aspect='auto', vmin=0, vmax=30)
        
        ax.set_xticks(range(len(risks)))
        ax.set_xticklabels([r.replace('pct_', '').replace('_', ' ').title() for r in risks], rotation=45, ha='right')
        ax.set_yticks(range(len(segments)))
        ax.set_yticklabels([s.title() for s in segments])
        
        for i in range(len(segments)):
            for j in range(len(risks)):
                ax.text(j, i, f'{matrix[i,j]:.1f}%', ha='center', va='center', color='white' if matrix[i,j] > 15 else 'black', fontsize=9)
        
        ax.set_title('Risk Heatmap')
        fig.colorbar(im, ax=ax, shrink=0.8)
        plt.tight_layout()
        
        if return_metadata:
            plt.close(fig)
            return ChartMetadata(x_label='Risk', y_label='Segment', title='Risk Heatmap', width_inches=8, height_inches=5)
        return self._fig_to_bytes(fig)
