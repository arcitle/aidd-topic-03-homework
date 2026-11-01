from django.core.management.base import BaseCommand, CommandError
from t_tech.invest import Client

from config.settings import TINKOFF_TOKEN
from dashboard.models import Share


class Command(BaseCommand):
    help = "Add shares to DB"

    def handle(self, *args, **options):
        if not TINKOFF_TOKEN:
            raise CommandError("TINKOFF_TOKEN не задан")

        created_count = 0
        with Client(TINKOFF_TOKEN) as client:
            shares = client.instruments.shares()
            for share in shares.instruments:
                _, created = Share.objects.get_or_create(
                    figi=share.figi,
                    defaults={
                        "name": share.name,
                        "isin": share.isin,
                        "ticker": share.ticker,
                        "currency": share.currency,
                        "uid": share.uid,
                    },
                )
                if created:
                    created_count += 1

        self.stdout.write(self.style.SUCCESS(f"Добавлено акций: {created_count}"))
