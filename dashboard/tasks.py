import logging
from decimal import Decimal
from django.db import transaction
from dashboard.models import PriceHistory, WatchItem, PriceAlert, Strategy, PortfolioTransaction, StrategyExecution

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
            price = Decimal(str(last_price))
            PriceHistory.objects.get_or_create(share=share, recorded_at=updated_at, defaults={"price": price})
            check_price_rules(share, price, updated_at)
        except Exception:
            logger.exception("Failed to update price for share %s", share.pk)


@transaction.atomic
def check_price_rules(share, price, recorded_at):
    """Record each target crossing once; re-arm it after price leaves the condition."""
    for item in WatchItem.objects.select_for_update().filter(share=share, active=True, target_price__isnull=False):
        reached = price >= item.target_price if item.direction == WatchItem.ABOVE else price <= item.target_price
        if reached and item.triggered_at is None:
            with transaction.atomic():
                PriceAlert.objects.get_or_create(item=item, triggered_at=recorded_at, defaults={"price": price})
                item.triggered_at = recorded_at
                item.save(update_fields=["triggered_at"])
        elif not reached and item.triggered_at is not None:
            item.triggered_at = None
            item.save(update_fields=["triggered_at"])

    for strategy in Strategy.objects.select_for_update().filter(share=share, active=True):
        reached = price >= strategy.target_price if strategy.operator == "above" else price <= strategy.target_price
        if not reached:
            if strategy.last_triggered_at:
                strategy.last_triggered_at = None
                strategy.save(update_fields=["last_triggered_at"])
            continue
        if strategy.last_triggered_at:
            continue
        with transaction.atomic():
            owned = sum((tx.quantity if tx.side == PortfolioTransaction.BUY else -tx.quantity for tx in strategy.portfolio.transactions.filter(share=share)), Decimal("0"))
            if strategy.side == Strategy.SELL and strategy.quantity > owned:
                continue
            tx = PortfolioTransaction.objects.create(portfolio=strategy.portfolio, share=share, side=strategy.side, quantity=strategy.quantity, price=price)
            StrategyExecution.objects.create(strategy=strategy, transaction=tx)
            strategy.last_triggered_at = recorded_at
            strategy.save(update_fields=["last_triggered_at"])
