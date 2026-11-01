from datetime import timedelta

from plotly.graph_objs import Scatter
from plotly.offline import plot
from t_tech.invest import CandleInterval, Client
from t_tech.invest.utils import now

from config.settings import TINKOFF_TOKEN


def get_graph(share):
    x_data, y_data = [], []
    if TINKOFF_TOKEN:
        with Client(TINKOFF_TOKEN) as client:
            for candle in client.get_all_candles(
                figi=share.figi,
                from_=now() - timedelta(days=180),
                interval=CandleInterval.CANDLE_INTERVAL_DAY,
            ):
                x_data.append(candle.time.date())
                y_data.append(candle.close.units + candle.close.nano / 1_000_000_000)
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
        show_link=False,
        link_text="",
    )
    return plot_div
