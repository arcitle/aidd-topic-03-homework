from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, View, UpdateView

from .forms import ShareModelForm
from .models import Share
from .services.graph import get_graph
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponseBadRequest
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from .models import WatchItem, PriceAlert, Portfolio, PortfolioTransaction, Strategy
from .forms import WatchItemForm, PortfolioTransactionForm, StrategyForm


class IsUserAuthenticatedMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated

    @staticmethod
    def handle_no_permission():
        return redirect("dashboard:index")


class ShareListView(ListView):
    """Список акций"""

    model = Share
    template_name = "dashboard/list.html"
    paginate_by = 100
    ordering = ["name"]


class ShareDetailView(View):
    @staticmethod
    def get(request, pk):
        share = get_object_or_404(Share, pk=pk)
        try:
            days = min(max(int(request.GET.get("days", 180)), 1), 3650)
        except ValueError:
            days = 180
        history = share.price_history.filter(recorded_at__gte=timezone.now() - timedelta(days=days)).order_by("recorded_at")
        first = history.first()
        last = history.last()
        change = last.price - first.price if first and last else None
        change_pct = (change / first.price * 100) if change is not None and first.price else None

        return render(
            request,
            "dashboard/detail.html",
            {"plot_div": get_graph(share, days=days), "share": share, "history": history, "days": days, "price_change": change, "price_change_pct": change_pct},
        )


def feature_home(request):
    if not request.user.is_authenticated:
        return redirect("user:auth")
    portfolio, _ = Portfolio.objects.get_or_create(user=request.user, name="Мой портфель")
    positions = []
    for share in Share.objects.all():
        buys = portfolio.transactions.filter(share=share, side=PortfolioTransaction.BUY)
        sells = portfolio.transactions.filter(share=share, side=PortfolioTransaction.SELL)
        bought = sum((x.quantity for x in buys), 0)
        sold = sum((x.quantity for x in sells), 0)
        qty = bought - sold
        if qty:
            cost = sum((x.quantity * x.price for x in buys), 0)
            avg = cost / bought if bought else 0
            current = Decimal(str(share.last_price or 0))
            positions.append({"share": share, "quantity": qty, "average": avg, "value": qty * current, "pnl": qty * (current - avg)})
    return render(request, "dashboard/features.html", {
        "portfolio": portfolio, "positions": positions,
        "watch_items": WatchItem.objects.filter(user=request.user).select_related("share"),
        "alerts": PriceAlert.objects.filter(item__user=request.user).select_related("item__share")[:50],
        "transactions": portfolio.transactions.select_related("share").order_by("-executed_at")[:50],
        "strategies": Strategy.objects.filter(user=request.user).select_related("share"),
        "watch_form": WatchItemForm(), "transaction_form": PortfolioTransactionForm(), "strategy_form": StrategyForm(),
    })


@login_required
def add_watch_item(request):
    if request.method != "POST": return HttpResponseBadRequest()
    form = WatchItemForm(request.POST)
    if form.is_valid():
        item, created = WatchItem.objects.update_or_create(user=request.user, share=form.cleaned_data["share"], defaults={"target_price": form.cleaned_data["target_price"], "direction": form.cleaned_data["direction"], "active": True, "triggered_at": None})
    else: messages.error(request, "Проверьте параметры целевой цены.")
    return redirect("dashboard:features")


@login_required
def add_transaction(request):
    if request.method != "POST": return HttpResponseBadRequest()
    form = PortfolioTransactionForm(request.POST)
    if form.is_valid():
        with transaction.atomic():
            portfolio, _ = Portfolio.objects.get_or_create(user=request.user, name="Мой портфель")
            Portfolio.objects.select_for_update().get(pk=portfolio.pk)
            tx = form.save(commit=False); tx.portfolio = portfolio
            current = sum((x.quantity if x.side == "buy" else -x.quantity for x in portfolio.transactions.filter(share=tx.share)), 0)
            if tx.side == "sell" and tx.quantity > current:
                messages.error(request, "Нельзя продать больше акций, чем есть в портфеле.")
            else: tx.save()
    else: messages.error(request, "Проверьте параметры сделки.")
    return redirect("dashboard:features")


@login_required
def add_strategy(request):
    if request.method != "POST": return HttpResponseBadRequest()
    portfolio, _ = Portfolio.objects.get_or_create(user=request.user, name="Мой портфель")
    form = StrategyForm(request.POST)
    if form.is_valid():
        strategy = form.save(commit=False); strategy.user = request.user; strategy.portfolio = portfolio; strategy.save()
    else: messages.error(request, "Проверьте параметры стратегии.")
    return redirect("dashboard:features")


class ShareCreateView(IsUserAuthenticatedMixin, CreateView):
    """Добавление инструмента"""

    template_name = "dashboard/create.html"
    form_class = ShareModelForm
    success_url = reverse_lazy("dashboard:index")


class ShareUpdateView(IsUserAuthenticatedMixin, UpdateView):
    """Редактирование инструмента"""

    model = Share
    template_name = "dashboard/create.html"
    form_class = ShareModelForm
    success_url = reverse_lazy("dashboard:index")


class ShareDeleteView(IsUserAuthenticatedMixin, DeleteView):
    """Удаление задачи"""

    model = Share
    template_name = "dashboard/delete.html"
    success_url = reverse_lazy("dashboard:index")
