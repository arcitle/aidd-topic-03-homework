import logging

from config.celery import app
from dashboard.models import Share
from dashboard.services.market_data import get_last_data

logger = logging.getLogger(__name__)


@app.task
def update_last_price():
    shares = Share.objects.all()

    for share in shares:
        try:
            last_price, updated_at = get_last_data(share)
            is_trend_high = share.last_price is None or last_price >= share.last_price
            Share.objects.filter(pk=share.pk).update(
                last_price=last_price,
                is_trend_high=is_trend_high,
                updated_at=updated_at,
            )
        except Exception:
            logger.exception("Failed to update price for share %s", share.pk)
