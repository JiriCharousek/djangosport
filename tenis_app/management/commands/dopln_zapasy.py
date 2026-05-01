import random
from django.core.management.base import BaseCommand
from tenis_app.models import Hrac, Zapas, Soutez

class Command(BaseCommand):
    help = 'Bezpečný restart všech lig bez rizika zacyklení'

    def handle(self, *args, **options):
        ligy_k_uprave = [
            {'slug': '26_kaminka_leto_A', 'klub': 'Léto 2026 - A'},
            {'slug': '26_kaminka_leto_B', 'klub': 'Léto 2026 - B'},
            {'slug': '26_kaminka_leto_C', 'klub': 'Léto 2026 - C'},
            {'slug': '26_kaminka_leto_D', 'klub': 'Léto 2026 - D'},
            {'slug': '26_kaminka_leto_E', 'klub': 'Léto 2026 - E'},
            {'slug': '26_kaminka_leto_z', 'klub': 'Léto 2026 - Ženy'},
        ]

        for liga in ligy_k_uprave:
            self.stdout.write(f"\n--- Zpracovávám ligu: {liga['klub']} ---")
            
            try:
                soutez = Soutez.objects.get(slug=liga['slug'])
                hraci = list(Hrac.objects.filter(klub=liga['klub']))
            except Soutez.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"Soutěž {liga['slug']} nenalezena."))
                continue

            if not hraci:
                self.stdout.write("V této lize nejsou žádní hráči.")
                continue

            # Smazání starých dat
            Zapas.objects.filter(soutez=soutez).delete()
            
            vsechny_dvojice = []
            for i in range(len(hraci)):
                for j in range(i + 1, len(hraci)):
                    vsechny_dvojice.append([hraci[i], hraci[j]])

            # Zamícháme pro náhodnost
            random.shuffle(vsechny_dvojice)

            # Sledování, kolikrát kdo už míče nese
            pocitadlo = {hrac.id: 0 for hrac in hraci}
            
            # Maximální počet pro každého (u 11 lidí je to 5)
            # Pokud je počet zápasů na hráče lichý, někdo bude mít o 1 víc
            pocet_zapasu_na_hrace = len(hraci) - 1
            idealni_limit = pocet_zapasu_na_hrace // 2

            for h1, h2 in vsechny_dvojice:
                # Rozhodnutí: Míče bere ten, kdo jich má zatím méně
                if pocitadlo[h1.id] <= pocitadlo[h2.id]:
                    domaci, host, bere_domaci = h1, h2, True
                    pocitadlo[h1.id] += 1
                else:
                    domaci, host, bere_domaci = h1, h2, False
                    pocitadlo[h2.id] += 1
                
                Zapas.objects.create(
                    soutez=soutez,
                    hrac_domaci=domaci,
                    hrac_hoste=host,
                    mice_bere_domaci=bere_domaci,
                    odehrano=False,
                    datum='2026-04-26'
                )

            self.stdout.write(self.style.SUCCESS(f"Liga {liga['klub']} hotova."))
            # Kontrolní výpis rozptylu
            vysledky = [str(pocitadlo[h.id]) for h in hraci]
            self.stdout.write(f"Rozdělení míčů: {', '.join(vysledky)}")

        self.stdout.write(self.style.SUCCESS('\nHotovo! Všechny ligy jsou vybalancovány.'))