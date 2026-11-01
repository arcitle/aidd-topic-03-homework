import logging

from t_tech.invest import Client

from config.settings import TINKOFF_TOKEN

logger = logging.getLogger(__name__)


def get_last_data(share):
    if not TINKOFF_TOKEN:
        raise RuntimeError("TINKOFF_TOKEN не задан")
    with Client(TINKOFF_TOKEN) as client:
        resp = client.market_data.get_last_prices(figi=[share.figi])
        if not resp.last_prices:
            raise LookupError(f"Поставщик не вернул цену для {share.ticker}")
        resp = resp.last_prices[0]
        logger.info(f"Get last data for share with id {share.id}")
        price = resp.price.units + resp.price.nano / 1_000_000_000
        return price, resp.time
