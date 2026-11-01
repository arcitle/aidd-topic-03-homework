import logging
from datetime import timedelta

from plotly.graph_objs import Scatter
from plotly.offline import plot
from t_tech.invest import CandleInterval, Client
from t_tech.invest.utils import now

from config.settings import TINKOFF_TOKEN

from .pricing import quotation_to_float

logger = logging.getLogger(__name__)


def get_graph(share):
    x_data, y_data = [], []

    if TINKOFF_TOKEN:
        try:
            with Client(TINKOFF_TOKEN) as client:
                for candle in client.get_all_candles(
                    figi=share.figi,
                    from_=now() - timedelta(days=180),
                    interval=CandleInterval.CANDLE_INTERVAL_DAY,
                ):
                    x_data.append(candle.time.date())
                    y_data.append(quotation_to_float(candle.close))
        except Exception:
            logger.exception("Failed to load price history for share %s", share.pk)

    return plot(
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
