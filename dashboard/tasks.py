import logging

from config.celery import app
from dashboard.models import Share
from dashboard.services.market_data import get_last_data

logger = logging.getLogger(__name__)


@app.task
def update_last_price():
    for share in Share.objects.all():
        try:
            last_price, market_time = get_last_data(share)
            is_trend_high = share.last_price is None or last_price >= share.last_price
            Share.objects.filter(pk=share.pk).update(
                last_price=last_price,
                is_trend_high=is_trend_high,
                updated_at=market_time,
            )
        except Exception:
            logger.exception("Failed to update price for share %s", share.pk)
