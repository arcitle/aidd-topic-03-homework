import logging

from t_tech.invest import Client

from config.settings import TINKOFF_TOKEN

from .pricing import quotation_to_float

logger = logging.getLogger(__name__)


def get_last_data(share):
    if not TINKOFF_TOKEN:
        raise RuntimeError("TINKOFF_TOKEN не задан")

    with Client(TINKOFF_TOKEN) as client:
        response = client.market_data.get_last_prices(figi=[share.figi])
        if not response.last_prices:
            raise LookupError(f"Поставщик не вернул цену для {share.ticker}")

        last_price = response.last_prices[0]
        logger.info("Get last data for share with id %s", share.id)
        return quotation_to_float(last_price.price), last_price.time
