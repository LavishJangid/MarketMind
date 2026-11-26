"""Streamlit entry point and navigation shell for MarketMind."""

from __future__ import annotations

import streamlit as st

from app.registry import (
    SUPPORTED_INDUSTRIES,
    IndustryDefinition,
    RegistryStatus,
    inspect_registry,
)
from app.ui.components import render_empty_state, render_error_state, render_page_header
from app.ui.theme import apply_base_styles
from app.views.overview import render_overview
from marketmind.config import Settings
from marketmind.errors import ConfigurationError
from marketmind.logging import configure_logging

OVERVIEW_PAGE = "Overview"
_INDUSTRY_BY_LABEL: dict[str, IndustryDefinition] = {
    industry.label: industry for industry in SUPPORTED_INDUSTRIES
}
_NAVIGATION_PAGES: tuple[str, ...] = (OVERVIEW_PAGE, *_INDUSTRY_BY_LABEL.keys())


def _render_sidebar(settings: Settings, registry: RegistryStatus) -> str:
    """Render the MarketMind navigation sidebar and return the selected page name."""
    with st.sidebar:
        st.markdown(f"### {settings.app_name}")
        st.caption("Multi-Industry BI & Data Science")
        st.divider()

        selected_page = st.radio(
            "Navigation",
            options=_NAVIGATION_PAGES,
            key="marketmind_navigation_page",
        )

        st.divider()
        st.caption("Runtime Configuration")
        st.text(f"Environment: {settings.environment}")
        st.text(f"Data dir: {settings.data_dir}")
        st.text(f"Datasets: {registry.total_datasets}")
    return str(selected_page)


def _render_industry_placeholder(
    industry: IndustryDefinition,
    registry: RegistryStatus,
) -> None:
    """Render an explicit empty state for an unimplemented industry analytics page."""
    datasets = registry.datasets_for_industry(industry.key)
    render_page_header(
        title=industry.label,
        subtitle=industry.description,
        badge="Analytics Pending",
    )
    if registry.error is not None:
        render_error_state(
            title="Dataset Registry Error",
            message=registry.error,
            detail=f"Inspected registry path: {registry.registry_path}",
        )
        return

    availability_note = (
        f"{len(datasets)} validated dataset(s) currently registered for {industry.label}."
        if datasets
        else f"No datasets are currently registered for {industry.label}."
    )
    render_empty_state(
        title=f"{industry.label} Analytics Not Yet Implemented",
        message=(
            "This workspace is part of the MarketMind navigation shell. "
            "Industry-specific KPIs, models, and Plotly visualizations will be enabled "
            "in a subsequent milestone."
        ),
        detail=availability_note,
    )


def run_app() -> None:
    """Configure Streamlit, initialize MarketMind settings, and render the active view."""
    st.set_page_config(
        page_title="MarketMind",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    apply_base_styles()

    try:
        settings = Settings.from_env()
    except ConfigurationError as exc:
        render_page_header(
            title="MarketMind",
            subtitle="Multi-Industry Business Intelligence & Data Science Platform",
            badge="Configuration Error",
        )
        render_error_state(
            title="Invalid Application Configuration",
            message=str(exc),
            detail="Verify MARKETMIND_* environment variables and reload the application.",
        )
        return

    configure_logging(settings)
    registry = inspect_registry(settings)
    selected_page = _render_sidebar(settings, registry)

    if selected_page == OVERVIEW_PAGE:
        render_overview(settings, registry)
    elif selected_page in _INDUSTRY_BY_LABEL:
        _render_industry_placeholder(_INDUSTRY_BY_LABEL[selected_page], registry)


if __name__ == "__main__":
    run_app()
