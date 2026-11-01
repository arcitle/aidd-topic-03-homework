from django import forms

from .models import Portfolio, Share, Strategy, Trade, WatchTarget


class ShareModelForm(forms.ModelForm):
    """Инструмент"""

    class Meta:
        model = Share
        fields = "__all__"


class WatchTargetForm(forms.ModelForm):
    class Meta:
        model = WatchTarget
        fields = ["share", "direction", "target_price"]


class TradeForm(forms.ModelForm):
    class Meta:
        model = Trade
        fields = ["share", "side", "quantity", "price"]

    def clean_quantity(self):
        value = self.cleaned_data["quantity"]
        if value <= 0:
            raise forms.ValidationError("Количество должно быть больше нуля")
        return value

    def clean_price(self):
        value = self.cleaned_data["price"]
        if value <= 0:
            raise forms.ValidationError("Цена должна быть больше нуля")
        return value


class StrategyForm(forms.ModelForm):
    class Meta:
        model = Strategy
        fields = ["name", "share", "action", "condition", "target_price", "quantity"]

    def clean(self):
        data = super().clean()
        if data.get("target_price", 0) <= 0 or data.get("quantity", 0) <= 0:
            raise forms.ValidationError("Цена и количество должны быть больше нуля")
        return data
