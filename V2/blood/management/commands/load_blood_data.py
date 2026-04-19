from django.core.management.base import BaseCommand
from blood.models import BloodType, BloodStock


class Command(BaseCommand):
    help = 'Initialize BloodType and BloodStock records'

    def handle(self, *args, **kwargs):
        specs = [
            ('A', '+'), ('A', '-'),
            ('B', '+'), ('B', '-'),
            ('AB', '+'), ('AB', '-'),
            ('O', '+'), ('O', '-'),
        ]
        for bt, bs in specs:
            obj, _ = BloodType.objects.get_or_create(blood_type=bt, blood_sign=bs)
            BloodStock.objects.get_or_create(blood_type=obj, defaults={'units_available': 0})
        self.stdout.write(self.style.SUCCESS(
            f'Initialized {BloodType.objects.count()} BloodTypes and {BloodStock.objects.count()} BloodStocks.'
        ))
