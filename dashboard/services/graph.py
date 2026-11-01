from datetime import timedelta
import logging

from plotly.graph_objs import Scatter
from plotly.offline import plot
from t_tech.invest import CandleInterval, Client
from t_tech.invest.utils import now

from config.settings import TINKOFF_TOKEN

logger = logging.getLogger(__name__)


def get_graph(share, days=180):
    x_data, y_data = [], []
    stored = list(share.price_history.filter(recorded_at__gte=now() - timedelta(days=days)).order_by("recorded_at").values_list("recorded_at", "price"))
    if stored:
        x_data = [point[0].date() for point in stored]
        y_data = [float(point[1]) for point in stored]
    if TINKOFF_TOKEN:
        try:
            with Client(TINKOFF_TOKEN) as client:
                for candle in client.get_all_candles(
                    figi=share.figi,
                    from_=now() - timedelta(days=180),
                    interval=CandleInterval.CANDLE_INTERVAL_DAY,
                ):
                    if not stored:
                        x_data.append(candle.time.date())
                        y_data.append(candle.close.units + candle.close.nano / 1_000_000_000)
        except Exception:
            logger.exception("Failed to load price history for share %s", share.pk)
    plot_div = plot(
        [
            Scatter(
                x=x_data,
                y=y_data,
                mode="lines",
                name=share.ticker,
                opacity=0.8,
                marker_color="red",
            )
        ],
        output_type="div",
        include_plotlyjs=False,
    )
    return plot_div
