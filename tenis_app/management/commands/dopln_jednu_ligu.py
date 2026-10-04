import random
from django.core.management.base import BaseCommand
from tenis_app.models import Hrac, Zapas, Soutez

class Command(BaseCommand):
    help = 'Vygeneruje zápasy dvoukolově, kde v každém zápase bere míče domácí hráč'

    def add_arguments(self, parser):
        parser.add_argument('slug', type=str, help='Slug ligy (např. 26_kaminka_leto_A)')

    def handle(self, *args, **options):
        slug = options['slug']

        # Načtení soutěže
        try:
            soutez = Soutez.objects.get(slug=slug)
        except Soutez.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Soutěž se slugem '{slug}' nebyla v databázi nalezena."))
            return

        klub_jmeno = soutez.nazev
        self.stdout.write(f"\n--- Zpracovávám ligu: {klub_jmeno} (slug: {slug}) ---")

        # Načtení hráčů
        hraci = list(Hrac.objects.filter(klub=klub_jmeno))

        if not hraci:
            self.stdout.write(self.style.WARNING(f"V lize '{klub_jmeno}' nebyly nalezeni žádní hráči."))
            return

        # Smazání starých zápasů
        smazano, _ = Zapas.objects.filter(soutez=soutez).delete()
        self.stdout.write(f"Smazáno {smazano} původních zápasů.")
        
        # Generování dvoukolových dvojic (každý s každým 2x: A->B i B->A)
        vsechny_dvojice = []
        for i in range(len(hraci)):
            for j in range(len(hraci)):
                if i != j:
                    vsechny_dvojice.append((hraci[i], hraci[j]))

        random.shuffle(vsechny_dvojice)
        
        # Počitadlo pro přehled ve výpisu
        pocitadlo = {hrac.id: 0 for hrac in hraci}

        for h1, h2 in vsechny_dvojice:
            # Vždy platí: domaci = h1, host = h2, a míče bere vždy domácí (True)
            domaci, host, bere_domaci = h1, h2, True
            pocitadlo[domaci.id] += 1
            
            Zapas.objects.create(
                soutez=soutez,
                hrac_domaci=domaci,
                hrac_hoste=host,
                mice_bere_domaci=bere_domaci,
                odehrano=False,
                datum=None
            )

        self.stdout.write(self.style.SUCCESS(f"Liga '{klub_jmeno}' byla úspěšně vygenerována (celkem {len(vsechny_dvojice)} zápasů)."))
        vysledky = [f"{h.jmeno}: {pocitadlo[h.id]}x 🎾" for h in hraci]
        self.stdout.write(f"Rozdělení míčů (domácí zápasy):\n" + "\n".join(vysledky))