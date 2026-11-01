from decimal import Decimal
from django.conf import settings
from django.db import models


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
    price = models.DecimalField(max_digits=18, decimal_places=6)
    recorded_at = models.DateTimeField(db_index=True)

    class Meta:
        ordering = ["recorded_at"]
        constraints = [models.UniqueConstraint(fields=["share", "recorded_at"], name="unique_share_price_time")]


class WatchTarget(models.Model):
    ABOVE = "above"
    BELOW = "below"
    DIRECTIONS = [(ABOVE, "Выше или равно"), (BELOW, "Ниже или равно")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="watch_targets")
    share = models.ForeignKey(Share, on_delete=models.CASCADE)
    target_price = models.DecimalField(max_digits=18, decimal_places=6)
    direction = models.CharField(max_length=5, choices=DIRECTIONS, default=ABOVE)
    active = models.BooleanField(default=True)
    condition_met = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class PriceAlert(models.Model):
    target = models.ForeignKey(WatchTarget, on_delete=models.CASCADE, related_name="alerts")
    triggered_at = models.DateTimeField(auto_now_add=True)
    price = models.DecimalField(max_digits=18, decimal_places=6)
    read = models.BooleanField(default=False)


class Portfolio(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="portfolios")
    name = models.CharField(max_length=100, default="Основной портфель")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "name")]


class Trade(models.Model):
    BUY = "buy"
    SELL = "sell"
    SIDE_CHOICES = [(BUY, "Покупка"), (SELL, "Продажа")]
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="trades")
    share = models.ForeignKey(Share, on_delete=models.CASCADE)
    side = models.CharField(max_length=4, choices=SIDE_CHOICES)
    quantity = models.DecimalField(max_digits=18, decimal_places=6)
    price = models.DecimalField(max_digits=18, decimal_places=6)
    created_at = models.DateTimeField(auto_now_add=True)
    strategy = models.ForeignKey("Strategy", null=True, blank=True, on_delete=models.SET_NULL, related_name="trades")


class Strategy(models.Model):
    BUY = "buy"
    SELL = "sell"
    ACTIONS = [(BUY, "Покупать"), (SELL, "Продавать")]
    ABOVE = "above"
    BELOW = "below"
    CONDITIONS = [(ABOVE, "Цена не ниже уровня"), (BELOW, "Цена не выше уровня")]
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="strategies")
    share = models.ForeignKey(Share, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    action = models.CharField(max_length=4, choices=ACTIONS)
    condition = models.CharField(max_length=5, choices=CONDITIONS)
    target_price = models.DecimalField(max_digits=18, decimal_places=6)
    quantity = models.DecimalField(max_digits=18, decimal_places=6)
    active = models.BooleanField(default=True)
    condition_met = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
