from config.celery import app
from dashboard.models import Share
from dashboard.services.market_data import get_last_data
from config.settings import logger


@app.task
def update_last_price():
    shares = Share.objects.all()

    for share in shares:
        try:
            last_price, _updated_at = get_last_data(share)
            is_trend_high = share.last_price is None or last_price >= share.last_price
            share.last_price = last_price
            share.is_trend_high = is_trend_high
            share.save(update_fields=("last_price", "is_trend_high", "updated_at"))
        except Exception as e:
            logger.error(e)
