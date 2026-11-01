from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, Case, When, F, DecimalField
from django.utils.dateparse import parse_date
from decimal import Decimal
from plotly.graph_objs import Scatter
from plotly.offline import plot
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView, View

from .forms import ShareModelForm, StrategyForm, TradeForm, WatchTargetForm
from .models import Portfolio, PriceAlert, PriceHistory, Share, Strategy, Trade, WatchTarget
from .services.graph import get_graph


class IsUserAuthenticatedMixin(UserPassesTestMixin):
    """Доступ только аутентифицированным; иначе redirect на главную (FR-12)."""

    def test_func(self):
        return self.request.user.is_authenticated

    def handle_no_permission(self):
        return redirect("dashboard:index")


class ShareListView(ListView):
    """Список акций"""

    model = Share
    template_name = "dashboard/list.html"
    paginate_by = 100
    ordering = ["name"]


class ShareDetailView(View):
    def get(self, request, pk):
        share = get_object_or_404(Share, pk=pk)
        return render(
            request,
            "dashboard/detail.html",
            {"plot_div": get_graph(share), "share": share,
             "history": share.price_history.order_by("-recorded_at")[:100]},
        )


class InvestorDashboardView(IsUserAuthenticatedMixin, View):
    template_name = "dashboard/investor.html"

    def get_portfolio(self, request):
        portfolio, _ = Portfolio.objects.get_or_create(user=request.user, name="Основной портфель")
        return portfolio

    def get(self, request):
        portfolio = self.get_portfolio(request)
        start = parse_date(request.GET.get("from", ""))
        end = parse_date(request.GET.get("to", ""))
        history = PriceHistory.objects.select_related("share").order_by("recorded_at")
        if request.GET.get("share"):
            history = history.filter(share_id=request.GET["share"])
        if start:
            history = history.filter(recorded_at__date__gte=start)
        if end:
            history = history.filter(recorded_at__date__lte=end)
        history = history.select_related("share")
        history_points = list(reversed(list(history.order_by("-recorded_at")[:500])))
        changes = {}
        grouped = {}
        for point in history_points:
            grouped.setdefault(point.share_id, []).append(point)
        for share_id, points in grouped.items():
            if len(points) > 1:
                first, last = points[0].price, points[-1].price
                changes[share_id] = {"absolute": last-first,
                                     "percent": ((last-first)/first*100 if first else None)}
        change_rows = [{"share": points[0].share, **changes[share_id]}
                       for share_id, points in grouped.items() if share_id in changes]
        history_graph = plot([
            Scatter(x=[p.recorded_at for p in points], y=[float(p.price) for p in points],
                    mode="lines+markers", name=points[0].share.ticker)
            for points in grouped.values()
        ], output_type="div", include_plotlyjs=False) if history_points else ""
        holdings = []
        for share in Share.objects.all():
            trades = portfolio.trades.filter(share=share)
            qty = Decimal("0")
            cost = Decimal("0")
            for trade in trades.order_by("created_at", "pk"):
                if trade.side == Trade.BUY:
                    qty += trade.quantity
                    cost += trade.quantity * trade.price
                elif qty:
                    sold = min(trade.quantity, qty)
                    cost -= cost / qty * sold
                    qty -= sold
            if qty <= 0:
                continue
            average = cost / qty
            current = Decimal(str(share.last_price or 0))
            holdings.append({"share": share, "quantity": qty, "average": average,
                             "value": qty * current, "pnl": qty * (current-average)})
        return render(request, self.template_name, {
            "portfolio": portfolio, "holdings": holdings,
            "watch_targets": WatchTarget.objects.filter(user=request.user).select_related("share").prefetch_related("alerts"),
            "alerts": PriceAlert.objects.filter(target__user=request.user).select_related("target__share")[:50],
            "trades": portfolio.trades.select_related("share").order_by("-created_at")[:100],
            "strategies": portfolio.strategies.select_related("share"),
            "watch_form": WatchTargetForm(), "trade_form": TradeForm(), "strategy_form": StrategyForm(),
            "history": history_points, "change_rows": change_rows, "history_graph": history_graph,
            "shares": Share.objects.all(),
        })

    @transaction.atomic
    def post(self, request):
        portfolio = self.get_portfolio(request)
        action = request.POST.get("action")
        if action == "watch":
            form = WatchTargetForm(request.POST)
            if form.is_valid():
                target = form.save(commit=False)
                target.user = request.user
                target.save()
                messages.success(request, "Целевой уровень добавлен")
            else:
                messages.error(request, form.errors)
        elif action == "trade":
            form = TradeForm(request.POST)
            if form.is_valid():
                data = form.cleaned_data
                if data["side"] == Trade.SELL:
                    net = portfolio.trades.filter(share=data["share"]).aggregate(qty=Sum(Case(When(side="buy", then=F("quantity")), default=-F("quantity"), output_field=DecimalField())))['qty'] or Decimal("0")
                    if data["quantity"] > net:
                        messages.error(request, "Недостаточно акций для продажи")
                        return redirect("dashboard:investor")
                Trade.objects.create(portfolio=portfolio, **data)
                messages.success(request, "Операция записана")
            else:
                messages.error(request, form.errors)
        elif action == "strategy":
            form = StrategyForm(request.POST)
            if form.is_valid():
                strategy = form.save(commit=False)
                strategy.portfolio = portfolio
                strategy.save()
                messages.success(request, "Стратегия создана")
            else:
                messages.error(request, form.errors)
        elif action == "delete_watch":
            WatchTarget.objects.filter(pk=request.POST.get("id"), user=request.user).delete()
        elif action == "toggle_strategy":
            Strategy.objects.filter(pk=request.POST.get("id"), portfolio=portfolio).update(active=~F("active"))
        return redirect("dashboard:investor")


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
    """Удаление акции"""

    model = Share
    template_name = "dashboard/delete.html"
    success_url = reverse_lazy("dashboard:index")
