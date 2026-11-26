"""Restrained visual design tokens, minimal layout styling, and Plotly defaults."""

from __future__ import annotations

from typing import Any

import streamlit as st

PALETTE: dict[str, Any] = {
    "ink": "#0F172A",
    "muted": "#475569",
    "subtle": "#64748B",
    "border": "#E2E8F0",
    "surface": "#F8FAFC",
    "accent": "#1D4ED8",
    "accent_soft": "#EFF6FF",
    "positive": "#0F766E",
    "warning": "#B45309",
    "danger": "#B91C1C",
    "chart_sequence": ("#1D4ED8", "#0F766E", "#475569", "#D97706", "#4338CA"),
}


def apply_base_styles() -> None:
    """Apply restrained layout spacing and card styling for the dashboard shell."""
    st.markdown(
        f"""
        <style>
        .block-container {{
            padding-top: 2rem;
            padding-bottom: 2.5rem;
            max-width: 1200px;
        }}
        .mm-header-badge {{
            display: inline-block;
            padding: 0.2rem 0.6rem;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 600;
            letter-spacing: 0.03em;
            text-transform: uppercase;
            color: {PALETTE["accent"]};
            background-color: {PALETTE["accent_soft"]};
            border: 1px solid #BFDBFE;
        }}
        .mm-status-pill {{
            display: inline-block;
            padding: 0.15rem 0.55rem;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 600;
        }}
        .mm-status-ready {{
            color: {PALETTE["positive"]};
            background-color: #CCFBF1;
        }}
        .mm-status-empty {{
            color: {PALETTE["muted"]};
            background-color: {PALETTE["surface"]};
            border: 1px solid {PALETTE["border"]};
        }}
        .mm-status-error {{
            color: {PALETTE["danger"]};
            background-color: #FEE2E2;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def plotly_layout_defaults(title: str | None = None) -> dict[str, Any]:
    """Return Plotly layout defaults aligned with the MarketMind visual palette."""
    layout: dict[str, Any] = {
        "font": {
            "family": "Inter, -apple-system, BlinkMacSystemFont, sans-serif",
            "size": 12,
            "color": PALETTE["ink"],
        },
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "colorway": list(PALETTE["chart_sequence"]),
        "margin": {"l": 40, "r": 24, "t": 44 if title else 24, "b": 40},
        "xaxis": {
            "gridcolor": PALETTE["border"],
            "zerolinecolor": PALETTE["border"],
        },
        "yaxis": {
            "gridcolor": PALETTE["border"],
            "zerolinecolor": PALETTE["border"],
        },
    }
    if title is not None:
        layout["title"] = {
            "text": title,
            "font": {"size": 15, "color": PALETTE["ink"]},
            "x": 0.0,
        }
    return layout
