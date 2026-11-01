import logging
from decimal import Decimal
from django.db import transaction

from config.celery import app
from dashboard.models import (PriceAlert, PriceHistory, Share, Strategy,
                              Trade, WatchTarget)
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
            price = Decimal(str(last_price))
            PriceHistory.objects.get_or_create(share=share, recorded_at=market_time, defaults={"price": price})
            evaluate_price_conditions(share, price, market_time)
        except Exception:
            logger.exception("Failed to update price for share %s", share.pk)


@transaction.atomic
def evaluate_price_conditions(share, price, at=None):
    """Create one alert/trade on entry into a target condition; re-arm after exit."""
    from django.utils import timezone
    at = at or timezone.now()
    for target in WatchTarget.objects.select_for_update().filter(share=share, active=True):
        met = price >= target.target_price if target.direction == WatchTarget.ABOVE else price <= target.target_price
        if met and not target.condition_met:
            PriceAlert.objects.create(target=target, price=price, triggered_at=at)
        if target.condition_met != met:
            target.condition_met = met
            target.save(update_fields=["condition_met"])
    for strategy in Strategy.objects.select_for_update().filter(share=share, active=True):
        met = price >= strategy.target_price if strategy.condition == Strategy.ABOVE else price <= strategy.target_price
        if met and not strategy.condition_met:
            portfolio = strategy.portfolio
            if strategy.action == Strategy.SELL:
                position = _position(portfolio, share)
                quantity = min(strategy.quantity, position[0])
                if quantity > 0:
                    Trade.objects.create(portfolio=portfolio, share=share, side=Trade.SELL,
                                         quantity=quantity, price=price, strategy=strategy)
            else:
                Trade.objects.create(portfolio=portfolio, share=share, side=Trade.BUY,
                                     quantity=strategy.quantity, price=price, strategy=strategy)
        if strategy.condition_met != met:
            strategy.condition_met = met
            strategy.save(update_fields=["condition_met"])


def _position(portfolio, share):
    quantity = cost = Decimal("0")
    for trade in portfolio.trades.filter(share=share).order_by("created_at", "pk"):
        if trade.side == Trade.BUY:
            quantity += trade.quantity
            cost += trade.quantity * trade.price
        elif quantity:
            sold = min(trade.quantity, quantity)
            cost -= (cost / quantity) * sold
            quantity -= sold
    return quantity, cost / quantity if quantity else Decimal("0")
