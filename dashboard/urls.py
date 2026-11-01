from django.urls import include, path

from dashboard.views import (
    ShareCreateView,
    ShareDeleteView,
    ShareDetailView,
    ShareListView,
    ShareUpdateView,
    feature_home, add_watch_item, add_transaction, add_strategy,
)

app_name = "dashboard"

urlpatterns = [
    path("", ShareListView.as_view(), name="index"),
    path("<int:pk>", ShareDetailView.as_view(), name="detail"),
    path("create", ShareCreateView.as_view(), name="create"),
    path("update/<int:pk>", ShareUpdateView.as_view(), name="update"),
    path("delete/<int:pk>", ShareDeleteView.as_view(), name="delete"),
    path("api/", include("dashboard.api.urls")),
    path("investments/", feature_home, name="features"),
    path("investments/watch/", add_watch_item, name="watch-add"),
    path("investments/transaction/", add_transaction, name="transaction-add"),
    path("investments/strategy/", add_strategy, name="strategy-add"),
]
