from django import forms

from .models import Share, WatchItem, PortfolioTransaction, Strategy


class ShareModelForm(forms.ModelForm):
    """Инструмент"""

    class Meta:
        model = Share
        fields = "__all__"


class WatchItemForm(forms.ModelForm):
    class Meta:
        model = WatchItem
        fields = ["share", "target_price", "direction"]
        widgets = {"target_price": forms.NumberInput(attrs={"step": "0.00000001"})}


class PortfolioTransactionForm(forms.ModelForm):
    class Meta:
        model = PortfolioTransaction
        fields = ["share", "side", "quantity", "price"]
        widgets = {"quantity": forms.NumberInput(attrs={"step": "0.00000001", "min": "0.00000001"}), "price": forms.NumberInput(attrs={"step": "0.00000001", "min": "0.00000001"})}


class StrategyForm(forms.ModelForm):
    class Meta:
        model = Strategy
        fields = ["name", "share", "side", "operator", "target_price", "quantity"]
        widgets = {"target_price": forms.NumberInput(attrs={"step": "0.00000001", "min": "0.00000001"}), "quantity": forms.NumberInput(attrs={"step": "0.00000001", "min": "0.00000001"})}
