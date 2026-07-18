"""System health service per spec Section 23."""

from __future__ import annotations

from typing import TYPE_CHECKING

from carpet_designer.cli import run_doctor

if TYPE_CHECKING:
    from carpet_designer.domain.schemas import DoctorReport


class HealthService:
    """Service for system health checks.

    Provides health status information for the System Health
    Streamlit page and CLI doctor command.
    """

    def check(self) -> DoctorReport:
        """Run all system health checks.

        Returns:
            DoctorReport with all check results.
        """
        return run_doctor()
