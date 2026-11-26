"""Reusable Streamlit UI components for MarketMind."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from html import escape

import streamlit as st


@dataclass(frozen=True, slots=True)
class KpiItem:
    """Display specification for a single KPI tile."""

    label: str
    value: str | int
    delta: str | None = None
    help_text: str | None = None


def render_page_header(
    title: str,
    subtitle: str | None = None,
    badge: str | None = None,
) -> None:
    """Render a consistent page header with optional environment or status badge."""
    if badge:
        st.markdown(
            f'<span class="mm-header-badge">{escape(badge)}</span>',
            unsafe_allow_html=True,
        )
    st.title(title)
    if subtitle:
        st.caption(subtitle)
    st.divider()


def render_kpi_card(item: KpiItem) -> None:
    """Render a single KPI card inside a clean bordered container."""
    with st.container(border=True):
        st.metric(
            label=item.label,
            value=item.value,
            delta=item.delta,
            help=item.help_text,
        )


def render_kpi_row(items: Sequence[KpiItem]) -> None:
    """Render a responsive horizontal row of KPI cards."""
    if not items:
        return
    columns = st.columns(len(items))
    for column, item in zip(columns, items, strict=True):
        with column:
            render_kpi_card(item)


def render_empty_state(
    title: str,
    message: str,
    detail: str | None = None,
) -> None:
    """Render a clear empty state without fabricated metrics or placeholder data."""
    with st.container(border=True):
        st.markdown(f"**{title}**")
        st.write(message)
        if detail:
            st.caption(detail)


def render_error_state(
    title: str,
    message: str,
    detail: str | None = None,
) -> None:
    """Render a structured application or configuration error message."""
    st.error(f"**{title}**\n\n{message}")
    if detail:
        st.caption(detail)
