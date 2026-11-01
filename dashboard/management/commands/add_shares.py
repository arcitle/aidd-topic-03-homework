from django.core.management.base import BaseCommand
from t_tech.invest import Client

from config.settings import TINKOFF_TOKEN
from dashboard.models import Share


class Command(BaseCommand):
    help = "Add shares to DB"

    def handle(self, *args, **options):
        with Client(TINKOFF_TOKEN) as client:
            shares = client.instruments.shares()
            for share in shares.instruments:
                Share.objects.get_or_create(
                    figi=share.figi,
                    name=share.name,
                    isin=share.isin,
                    ticker=share.ticker,
                    currency=share.currency,
                    uid=share.uid,
                )


