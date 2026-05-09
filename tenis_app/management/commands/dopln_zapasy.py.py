from django.core.management.base import BaseCommand
from django.db.models import Q
from tenis_app.models import Hrac, Zapas, Soutez

class Command(BaseCommand):
    help = 'Doplní chybějící zápasy pro systém každý s každým v lize D'

    def handle(self, *args, **options):
        slug_souteze = '26_kaminka_leto_D'
        try:
            soutez = Soutez.objects.get(slug=slug_souteze)[cite: 1]
        except Soutez.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Soutěž {slug_souteze} nebyla nalezena!'))
            return

        # Získání hráčů (uprav filtr dle své potřeby, pokud je klub jiný)
        hraci = list(Hrac.objects.filter(klub='Léto 2026 - D'))[cite: 1]
        
        self.stdout.write(f"Kontroluji zápasy pro {len(hraci)} hráčů...")

        vytvoreno = 0
        
        for i in range(len(hraci)):
            for j in range(i + 1, len(hraci)):
                h1 = hraci[i]
                h2 = hraci[j]
                
                # Kontrola existence zápasu v obou směrech
                existuje = Zapas.objects.filter(
                    soutez=soutez
                ).filter(
                    (Q(hrac_domaci=h1) & Q(hrac_hoste=h2)) | 
                    (Q(hrac_domaci=h2) & Q(hrac_hoste=h1))
                ).exists()[cite: 1]
                
                if not existuje:
                    Zapas.objects.create(
                        soutez=soutez,
                        hrac_domaci=h1,
                        hrac_hoste=h2,
                        datum='2026-04-26', # Výchozí datum
                        odehrano=False[cite: 1]
                    )
                    self.stdout.write(f"Vytvořeno: {h1.jmeno} vs {h2.jmeno}")
                    vytvoreno += 1

        self.stdout.write(self.style.SUCCESS(f'Hotovo. Doplněno {vytvoreno} chybějících zápasů.'))
        
        
        C:\Users\jchar\djangoSport\tenis_app\models.py
        
        docker cp  C:\Users\jchar\djangoSport\tenis_app\models.py 24e6f0343a3b:/app/tenis_app/models.py