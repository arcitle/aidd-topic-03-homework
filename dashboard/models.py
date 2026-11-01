from django.db import models
from django.conf import settings


class Share(models.Model):
    """Акция"""

    figi = models.CharField(max_length=255, unique=True)
    isin = models.CharField(max_length=255)
    name = models.CharField(max_length=255, verbose_name="Наименование компании")
    ticker = models.CharField(max_length=10, unique=True, verbose_name="Тикер")
    currency = models.CharField(max_length=20, verbose_name="Валюта")
    uid = models.CharField(max_length=255, unique=True)
    last_price = models.FloatField(blank=True, null=True, verbose_name="Текущая цена")
    is_trend_high = models.BooleanField(
        blank=True, null=True, verbose_name="Растет цена"
    )
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        verbose_name = "Акция"
        verbose_name_plural = "Акции"


class PriceHistory(models.Model):
    share = models.ForeignKey(Share, on_delete=models.CASCADE, related_name="price_history")
    price = models.DecimalField(max_digits=20, decimal_places=8)
    recorded_at = models.DateTimeField(db_index=True)

    class Meta:
        ordering = ["recorded_at"]
        constraints = [models.UniqueConstraint(fields=["share", "recorded_at"], name="v2_unique_share_price_time")]
        db_table = "dashboard_v2_price_history"


class WatchItem(models.Model):
    ABOVE = "above"
    BELOW = "below"
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    share = models.ForeignKey(Share, on_delete=models.CASCADE)
    target_price = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    direction = models.CharField(max_length=5, choices=[(ABOVE, "Достигла или выше"), (BELOW, "Достигла или ниже")], default=ABOVE)
    active = models.BooleanField(default=True)
    triggered_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "share"], name="v2_unique_user_watch_share")]
        db_table = "dashboard_v2_watch_item"


class PriceAlert(models.Model):
    item = models.ForeignKey(WatchItem, on_delete=models.CASCADE, related_name="alerts")
    price = models.DecimalField(max_digits=20, decimal_places=8)
    triggered_at = models.DateTimeField()
    class Meta:
        constraints = [models.UniqueConstraint(fields=["item", "triggered_at"], name="v2_unique_alert_event_time")]
        db_table = "dashboard_v2_price_alert"


class Portfolio(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="portfolios")
    name = models.CharField(max_length=100, default="Мой портфель")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "name"], name="v2_unique_user_portfolio_name")]
        db_table = "dashboard_v2_portfolio"


class PortfolioTransaction(models.Model):
    BUY = "buy"
    SELL = "sell"
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="transactions")
    share = models.ForeignKey(Share, on_delete=models.PROTECT)
    side = models.CharField(max_length=4, choices=[(BUY, "Покупка"), (SELL, "Продажа")])
    quantity = models.DecimalField(max_digits=20, decimal_places=8)
    price = models.DecimalField(max_digits=20, decimal_places=8)
    executed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "dashboard_v2_portfolio_transaction"


class Strategy(models.Model):
    BUY = "buy"
    SELL = "sell"
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="strategies")
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="strategies")
    share = models.ForeignKey(Share, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    side = models.CharField(max_length=4, choices=[(BUY, "Покупать"), (SELL, "Продавать")])
    operator = models.CharField(max_length=5, choices=[("below", "Цена не выше"), ("above", "Цена не ниже")])
    target_price = models.DecimalField(max_digits=20, decimal_places=8)
    quantity = models.DecimalField(max_digits=20, decimal_places=8)
    active = models.BooleanField(default=True)
    last_triggered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "dashboard_v2_strategy"


class StrategyExecution(models.Model):
    strategy = models.ForeignKey(Strategy, on_delete=models.CASCADE, related_name="executions")
    transaction = models.OneToOneField(PortfolioTransaction, on_delete=models.CASCADE)
    executed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "dashboard_v2_strategy_execution"
