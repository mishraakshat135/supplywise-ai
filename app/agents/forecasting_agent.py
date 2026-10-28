from __future__ import annotations

from app.agents.base import AgentContext, BaseAgent
from app.services.forecast_service import ForecastService


class ForecastingAgent(BaseAgent):
    """Predicts future demand. Delegates to ForecastService (ML member plugs models in ml/)."""
    name = "forecasting_agent"

    def execute(self, ctx: AgentContext):
        # TODO(INTEGRATION: ML): nothing to change here when a better model is added -
        # ForecastService picks it up automatically (see services/forecast_service.py).
        return ForecastService(ctx.db).forecast(ctx.product_id, ctx.request.horizon_days)
