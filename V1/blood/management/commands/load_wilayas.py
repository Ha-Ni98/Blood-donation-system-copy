import os
import json
from django.core.management.base import BaseCommand
from django.conf import settings
from blood.models import Wilaya, Commune

class Command(BaseCommand):
    help = 'Load 69 Wilayas and their Communes from static JSON Dataset'

    def handle(self, *args, **kwargs):
        json_path = os.path.join(settings.STATICFILES_DIRS[0], 'wilayas-with-municipalities.json')
        
        if not os.path.exists(json_path):
            # Fallback for when STATICFILES_DIRS is not used in this way
            json_path = os.path.join(settings.BASE_DIR, 'static/wilayas-with-municipalities.json')

        if not os.path.exists(json_path):
            self.stdout.write(self.style.ERROR(f'JSON file not found at {json_path}'))
            return

        self.stdout.write('Loading wilayas and communes from full JSON dataset...')
        
        # Clear existing data as we are starting fresh in dev
        Commune.objects.all().delete()
        Wilaya.objects.all().delete()
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            for w_data in data:
                wilaya = Wilaya.objects.create(
                    code=str(w_data['wilayaCode']),
                    name=w_data['nameFr']
                )
                
                communes_to_create = []
                for c_data in w_data.get('communes', []):
                    communes_to_create.append(Commune(
                        name=c_data['nameFr'],
                        wilaya=wilaya
                    ))
                Commune.objects.bulk_create(communes_to_create)

            self.stdout.write(self.style.SUCCESS(
                f'Successfully loaded {Wilaya.objects.count()} Wilayas and {Commune.objects.count()} Communes.'
            ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to load JSON: {str(e)}'))
