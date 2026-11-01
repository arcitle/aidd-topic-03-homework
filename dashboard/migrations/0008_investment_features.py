import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def ensure_investment_tables(apps, schema_editor):
    """Complete this migration if an earlier startup created only some tables."""
    from dashboard import models as current_models

    names = [
        "Portfolio", "PriceHistory", "WatchItem", "PriceAlert",
        "PortfolioTransaction", "Strategy", "StrategyExecution",
    ]
    with schema_editor.connection.cursor() as cursor:
        existing = set(schema_editor.connection.introspection.table_names(cursor))
    for name in names:
        model = getattr(current_models, name)
        if model._meta.db_table not in existing:
            schema_editor.create_model(model)
            existing.add(model._meta.db_table)

    # A table may have been created before a prior attempt failed while adding
    # constraints. Add any missing constraints without touching existing data.
    for name in names:
        model = getattr(current_models, name)
        with schema_editor.connection.cursor() as cursor:
            existing_constraints = schema_editor.connection.introspection.get_constraints(cursor, model._meta.db_table)
        for constraint in model._meta.constraints:
            if constraint.name not in existing_constraints:
                schema_editor.add_constraint(model, constraint)


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("dashboard", "0007_add_updated_at"),
    ]

    operations = [migrations.SeparateDatabaseAndState(
        database_operations=[migrations.RunPython(ensure_investment_tables, migrations.RunPython.noop)],
        state_operations=[
        migrations.CreateModel(name="Portfolio", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("name", models.CharField(default="Мой портфель", max_length=100)), ("created_at", models.DateTimeField(auto_now_add=True)), ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="portfolios", to=settings.AUTH_USER_MODEL))], options={"db_table": "dashboard_v2_portfolio"}),
        migrations.CreateModel(name="PriceHistory", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("price", models.DecimalField(decimal_places=8, max_digits=20)), ("recorded_at", models.DateTimeField(db_index=True)), ("share", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="price_history", to="dashboard.share"))], options={"ordering": ["recorded_at"], "db_table": "dashboard_v2_price_history"}),
        migrations.CreateModel(name="WatchItem", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("target_price", models.DecimalField(blank=True, decimal_places=8, max_digits=20, null=True)), ("direction", models.CharField(choices=[("above", "Достигла или выше"), ("below", "Достигла или ниже")], default="above", max_length=5)), ("active", models.BooleanField(default=True)), ("triggered_at", models.DateTimeField(blank=True, null=True)), ("share", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="dashboard.share")), ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL))], options={"db_table": "dashboard_v2_watch_item"}),
        migrations.CreateModel(name="PriceAlert", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("price", models.DecimalField(decimal_places=8, max_digits=20)), ("triggered_at", models.DateTimeField()), ("item", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="alerts", to="dashboard.watchitem"))], options={"db_table": "dashboard_v2_price_alert"}),
        migrations.CreateModel(name="PortfolioTransaction", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("side", models.CharField(choices=[("buy", "Покупка"), ("sell", "Продажа")], max_length=4)), ("quantity", models.DecimalField(decimal_places=8, max_digits=20)), ("price", models.DecimalField(decimal_places=8, max_digits=20)), ("executed_at", models.DateTimeField(auto_now_add=True)), ("portfolio", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="transactions", to="dashboard.portfolio")), ("share", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="dashboard.share"))], options={"db_table": "dashboard_v2_portfolio_transaction"}),
        migrations.CreateModel(name="Strategy", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("name", models.CharField(max_length=100)), ("side", models.CharField(choices=[("buy", "Покупать"), ("sell", "Продавать")], max_length=4)), ("operator", models.CharField(choices=[("below", "Цена не выше"), ("above", "Цена не ниже")], max_length=5)), ("target_price", models.DecimalField(decimal_places=8, max_digits=20)), ("quantity", models.DecimalField(decimal_places=8, max_digits=20)), ("active", models.BooleanField(default=True)), ("last_triggered_at", models.DateTimeField(blank=True, null=True)), ("portfolio", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="strategies", to="dashboard.portfolio")), ("share", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="dashboard.share")), ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="strategies", to=settings.AUTH_USER_MODEL))], options={"db_table": "dashboard_v2_strategy"}),
        migrations.CreateModel(name="StrategyExecution", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("executed_at", models.DateTimeField(auto_now_add=True)), ("strategy", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="executions", to="dashboard.strategy")), ("transaction", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to="dashboard.portfoliotransaction"))], options={"db_table": "dashboard_v2_strategy_execution"}),
        migrations.AddConstraint(model_name="pricehistory", constraint=models.UniqueConstraint(fields=("share", "recorded_at"), name="v2_unique_share_price_time")),
        migrations.AddConstraint(model_name="watchitem", constraint=models.UniqueConstraint(fields=("user", "share"), name="v2_unique_user_watch_share")),
        migrations.AddConstraint(model_name="pricealert", constraint=models.UniqueConstraint(fields=("item", "triggered_at"), name="v2_unique_alert_event_time")),
        migrations.AddConstraint(model_name="portfolio", constraint=models.UniqueConstraint(fields=("user", "name"), name="v2_unique_user_portfolio_name")),
        ],
    )]
