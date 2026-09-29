"""Shared query parameters for the analysis-scoped collection routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import Query

AnalysisId = Annotated[str, Query(description="ID returned by POST /analyses")]
Page = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=100)]
Descending = Annotated[bool, Query(alias="descending")]
