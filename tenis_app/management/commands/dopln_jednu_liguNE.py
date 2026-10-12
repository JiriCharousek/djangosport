from itertools import combinations
from django.core.management.base import BaseCommand
from tenis_app.models import Hrac, Zapas, Soutez

class Command(BaseCommand):
    help = 'Vygeneruje zápasy pro soutěž podle jejího typu (1K nebo 2K)'

    def add_arguments(self, parser):
        parser.add_argument('slug', type=str, help='Slug ligy (např. 27_kaminka_zima_mx)')

    def handle(self, *args, **options):
        slug = options['slug']

        try:
            soutez = Soutez.objects.get(slug=slug)
        except Soutez.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Soutěž se slugem '{slug}' nebyla v databázi nalezena."))
            return

        self.stdout.write(f"\n--- Zpracovávám ligu: {soutez.nazev} (slug: {slug}, typ: {soutez.typ}) ---")

        # Načtení hráčů přímo z vazby soutěže
        hraci = list(soutez.hraci.all())
        n = len(hraci)

        if n < 2:
            self.stdout.write(self.style.WARNING(f"V lize '{soutez.nazev}' není dostatek hráčů."))
            return

        # Smazání starých zápasů
        smazano, _ = Zapas.objects.filter(soutez=soutez).delete()
        self.stdout.write(f"Smazáno {smazano} původních zápasů.")
        
        vytvoreno = 0
        pocitadlo = {hrac.id: 0 for hrac in hraci}

        # --- JEDNOKOLOVÁ SOUTĚŽ (1K) ---
        if soutez.typ == '1K':
            for idx, (h1, h2) in enumerate(combinations(hraci, 2)):
                # Střídání míčků
                bere_domaci = (idx % 2 == 0)
                pocitadlo[h1.id] += 1 if bere_domaci else 0
                pocitadlo[h2.id] += 0 if bere_domaci else 1

                Zapas.objects.create(
                    soutez=soutez,
                    hrac_domaci=h1,
                    hrac_hoste=h2,
                    mice_bere_domaci=bere_domaci,
                    odehrano=False,
                    datum=None
                )
                vytvoreno += 1

        # --- DVOUKOLOVÁ SOUTĚŽ (2K) ---
        else:
            for i in range(n):
                for j in range(n):
                    if i != j:
                        h1, h2 = hraci[i], hraci[j]
                        bere_domaci = True if i < j else False
                        if bere_domaci:
                            pocitadlo[h1.id] += 1

                        Zapas.objects.create(
                            soutez=soutez,
                            hrac_domaci=h1,
                            hrac_hoste=h2,
                            mice_bere_domaci=bere_domaci,
                            odehrano=False,
                            datum=None
                        )
                        vytvoreno += 1

        self.stdout.write(self.style.SUCCESS(f"Liga '{soutez.nazev}' byla úspěšně vygenerována (celkem {vytvoreno} zápasů)."))
        vysledky = [f"{h.jmeno}: {pocitadlo[h.id]}x 🎾" for h in hraci]
        self.stdout.write(f"Rozdělení míčů (domácí zápasy):\n" + "\n".join(vysledky))