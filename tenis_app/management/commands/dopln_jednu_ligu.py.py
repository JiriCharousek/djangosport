import random
from django.core.management.base import BaseCommand
from tenis_app.models import Hrac, Zapas, Soutez

class Command(BaseCommand):
    help = 'Vygeneruje zápasy pro jednu konkrétní ligu podle zadaného slugu'

    def add_arguments(self, parser):
        # Přidáme povinný argument pro slug ligy
        parser.add_argument('slug', type=str, help='Slug ligy (např. 26_kaminka_leto_A)')

    def handle(self, *args, **options):
        slug = options['slug']

        # Definice lig (mapování slugu na název klubu pro filtraci hráčů)
        # Toto zůstává stejné jako v dopln_zapasy_2.py
        ligy_mapa = {
            '26_kaminka_leto_A': 'Léto 2026 - A',
            '26_kaminka_leto_B': 'Léto 2026 - B',
            '26_kaminka_leto_C': 'Léto 2026 - C',
            '26_kaminka_leto_D': 'Léto 2026 - D',
            '26_kaminka_leto_E': 'Léto 2026 - E',
            '26_kaminka_leto_z': 'Léto 2026 - Ženy',
        }

        if slug not in ligy_mapa:
            self.stdout.write(self.style.ERROR(f"Slug '{slug}' není v seznamu povolených lig."))
            return

        klub_jmeno = ligy_mapa[slug]
        self.stdout.write(f"\n--- Zpracovávám ligu: {klub_jmeno} (slug: {slug}) ---")
        
        try:
            soutez = Soutez.objects.get(slug=slug)
            hraci = list(Hrac.objects.filter(klub=klub_jmeno))
        except Soutez.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Soutěž se slugem {slug} nebyla v databázi nalezena."))
            return

        if not hraci:
            self.stdout.write(self.style.WARNING("V této lize nejsou žádní hráči."))
            return

        # Smazání starých dat pouze pro tuto ligu
        smazano, _ = Zapas.objects.filter(soutez=soutez).delete()
        self.stdout.write(f"Smazáno {smazano} původních zápasů.")
        
        vsechny_dvojice = []
        for i in range(len(hraci)):
            for j in range(i + 1, len(hraci)):
                vsechny_dvojice.append([hraci[i], hraci[j]])

        random.shuffle(vsechny_dvojice)
        pocitadlo = {hrac.id: 0 for hrac in hraci}

        for h1, h2 in vsechny_dvojice:
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
                datum=None
            )

        self.stdout.write(self.style.SUCCESS(f"Liga {klub_jmeno} byla úspěšně vygenerována."))
        vysledky = [f"{h.jmeno}: {pocitadlo[h.id]}x" for h in hraci]
        self.stdout.write(f"Rozdělení míčů: {', '.join(vysledky)}")