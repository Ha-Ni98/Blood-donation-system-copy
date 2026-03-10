from django.core.management.base import BaseCommand
from django.core.management import call_command
from blood.models import Wilaya, Commune
import os

class Command(BaseCommand):
    help = 'Load Wilayas and Communes from fixtures'

    def handle(self, *args, **kwargs):
        self.stdout.write('Loading wilayas and communes...')
        
        # Check if already loaded
        if Wilaya.objects.exists():
            self.stdout.write(self.style.WARNING('Wilayas already exist in database. Skipping...'))
            return
            
        try:
            call_command('loaddata', 'wilayas.json')
            self.stdout.write(self.style.SUCCESS(f'Successfully loaded {Wilaya.objects.count()} Wilayas and {Commune.objects.count()} Communes.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to load fixture: {str(e)}'))
