"""Overview page for MarketMind platform status and dataset availability."""

from __future__ import annotations

from html import escape

import streamlit as st

from app.registry import SUPPORTED_INDUSTRIES, IndustryDefinition, RegistryStatus
from app.ui.components import (
    KpiItem,
    render_empty_state,
    render_error_state,
    render_kpi_row,
    render_page_header,
)
from marketmind.config import Settings


def _render_industry_card(industry: IndustryDefinition, registry: RegistryStatus) -> None:
    """Render an industry availability card backed strictly by registry metadata."""
    datasets = registry.datasets_for_industry(industry.key)
    if registry.error is not None:
        pill_class = "mm-status-error"
        pill_label = "Registry Error"
    elif datasets:
        pill_class = "mm-status-ready"
        pill_label = f"{len(datasets)} Available"
    else:
        pill_class = "mm-status-empty"
        pill_label = "No Datasets"

    with st.container(border=True):
        st.markdown(
            f'<span class="mm-status-pill {pill_class}">{escape(pill_label)}</span>',
            unsafe_allow_html=True,
        )
        st.subheader(industry.label)
        st.write(industry.description)
        st.divider()
        if datasets:
            for dataset in datasets:
                timestamp = dataset.created_at.strftime("%Y-%m-%d %H:%M %Z")
                source_suffix = f" · Source: `{dataset.source}`" if dataset.source else ""
                st.markdown(
                    f"- **{escape(dataset.name)}** (`{escape(dataset.dataset_id)}`)  \n"
                    f"  Registered: {timestamp}{source_suffix}"
                )
        else:
            st.caption(
                "No validated datasets are currently registered for this industry."
            )


def render_overview(settings: Settings, registry: RegistryStatus) -> None:
    """Render the MarketMind Overview page."""
    render_page_header(
        title="Platform Overview",
        subtitle=(
            "Multi-industry business intelligence workspace and live dataset registry status."
        ),
        badge=f"{settings.environment} environment",
    )

    st.markdown(
        f"**{escape(settings.app_name)}** organizes analytics across three core industry "
        "verticals—Retail & E-commerce, Banking & Marketing, and Hospitality—using shared "
        "configuration and validated dataset contracts. All availability indicators below "
        "reflect the inspected dataset registry directly without simulated data."
    )

    registry_state_label = (
        "Error"
        if registry.error is not None
        else ("Ready" if registry.registry_exists else "Not Initialized")
    )
    render_kpi_row(
        [
            KpiItem(
                label="Registered Datasets",
                value=registry.total_datasets,
                help_text="Count of validated DatasetMetadata entries in the registry.",
            ),
            KpiItem(
                label="Active Industries",
                value=f"{registry.active_industry_count} / {len(SUPPORTED_INDUSTRIES)}",
                help_text="Supported industry verticals with at least one registered dataset.",
            ),
            KpiItem(
                label="Registry Status",
                value=registry_state_label,
                help_text=f"Inspected path: {registry.registry_path}",
            ),
            KpiItem(
                label="Log Level",
                value=settings.log_level,
                help_text="Active application logging threshold from Settings.",
            ),
        ]
    )

    st.write("")
    if registry.error is not None:
        render_error_state(
            title="Dataset Registry Could Not Be Loaded",
            message=registry.error,
            detail=f"Inspected registry file: {registry.registry_path}",
        )
    elif not registry.registry_exists:
        render_empty_state(
            title="No Dataset Registry Initialized",
            message=(
                "No dataset registry file was found in the configured data directory. "
                "Industry workspaces remain inactive until datasets are registered."
            ),
            detail=f"Configured registry path: {registry.registry_path}",
        )
    elif registry.total_datasets == 0:
        render_empty_state(
            title="Dataset Registry Is Empty",
            message=(
                "The registry file exists and is valid, but contains zero registered datasets."
            ),
            detail=f"Configured registry path: {registry.registry_path}",
        )

    st.subheader("Supported Industries")
    columns = st.columns(len(SUPPORTED_INDUSTRIES))
    for column, industry in zip(columns, SUPPORTED_INDUSTRIES, strict=True):
        with column:
            _render_industry_card(industry, registry)
