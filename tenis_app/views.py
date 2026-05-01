from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q, F
from django.utils import timezone
from django.urls import reverse
from .models import Hrac, Zapas, Soutez
from .forms import HracForm, ZapasForm
from django.contrib.auth.decorators import login_required
# =================================================================
# 1. UNIVERZÁLNÍ VÝPOČETNÍ JÁDRO (Modulární systém)
# =================================================================


def vypocitej_tabulku_dat(soutez, request=None):
    # 1. Základní queryset zápasů této soutěže
    # Změňte tento řádek:
    zapasy_v_soutezi = Zapas.objects.filter(soutez=soutez)

    vybrany_hrac = None
    # DEBUG: Pokud uvidíte v konzoli 0, víme, že zápasy mají v DB jinou soutěž
    print(f"DEBUG: Soutěž '{soutez.nazev}' (ID: {soutez.id}) má {zapasy_v_soutezi.count()} zápasů.")
    # 3. Identifikace hráčů - Zkusíme tři způsoby, jak je najít
    # A) Podle ID ze zápasů, které jsou v této soutěži
    id_hracu = set()
    for z in zapasy_v_soutezi:
        id_hracu.add(z.hrac_domaci_id)
        id_hracu.add(z.hrac_hoste_id)
    
    hraci_obj = list(Hrac.objects.filter(id__in=id_hracu))

    # B) Pokud zápasy ještě nejsou, zkusíme najít hráče podle jména soutěže (např. "Léto 2026 - D")
    if not hraci_obj:
        hraci_obj = list(Hrac.objects.filter(klub__icontains=soutez.nazev))

    # C) Pokud ani to nepomůže, zkusíme najít hráče podle koncového písmene (např. jen "D")
    if not hraci_obj:
        pismeno = soutez.nazev.split('-')[-1].strip() if '-' in soutez.nazev else soutez.nazev
        hraci_obj = list(Hrac.objects.filter(klub__icontains=pismeno))

    # 4. Příprava základních seznamů (RAW data pro výpočty)
    vsechny_odehrane = zapasy_v_soutezi.filter(odehrano=True).order_by('-datum', '-id')
    planovane_zapasy = zapasy_v_soutezi.filter(odehrano=False).order_by('-datum', 'id')

    # Tyto proměnné budeme filtrovat pouze pro zobrazení v seznamech
    zobrazit_historii = vsechny_odehrane
    zobrazit_plan = planovane_zapasy

    # 5. Zpracování filtru (pokud je request)
    if request:
        filtr_hrac_id = request.GET.get('filtr_hrac')
        if filtr_hrac_id and filtr_hrac_id.isdigit():
            vybrany_hrac = Hrac.objects.filter(id=filtr_hrac_id).first()
            if vybrany_hrac:
                # Filtrujeme pouze verze pro zobrazení
                zobrazit_historii = vsechny_odehrane.filter(
                    Q(hrac_domaci=vybrany_hrac) | Q(hrac_hoste=vybrany_hrac)
                )
                zobrazit_plan = planovane_zapasy.filter(
                    Q(hrac_domaci=vybrany_hrac) | Q(hrac_hoste=vybrany_hrac)
                )

    # --- VÝPOČET STATISTIKY MÍČŮ V PLÁNU ---
    for h in hraci_obj:
        # Používáme nefiltrované planovane_zapasy
        h.pocet_micku_v_planu = planovane_zapasy.filter(
            Q(hrac_domaci=h, mice_bere_domaci=True) | 
            Q(hrac_hoste=h, mice_bere_domaci=False)
        ).count()
    
    # 6. Výpočet bodů pro tabulku
    for h in hraci_obj:
        h.pocet_bodu, h.s_v, h.s_p = 0, 0, 0
        # Používáme základní zapasy_v_soutezi (nefiltrované filtrem hráče)
        zps = zapasy_v_soutezi.filter(odehrano=True).filter(Q(hrac_domaci=h) | Q(hrac_hoste=h))
        
        for z in zps:
            sd = z.sety_domaci if z.sety_domaci is not None else 0
            sh = z.sety_hoste if z.sety_hoste is not None else 0
            
            if z.hrac_domaci == h:
                h.s_v += sd
                h.s_p += sh
                bd, _ = z.ziskej_body()
                h.pocet_bodu += bd
            else:
                h.s_v += sh
                h.s_p += sd
                _, bh = z.ziskej_body()
                h.pocet_bodu += bh

    # Seřazení tabulky
    hraci_obj.sort(key=lambda x: (x.pocet_bodu, (x.s_v - x.s_p), x.s_v), reverse=True)

    # 7. Křížová tabulka (Matice)
    matice = []
    for h_radek in hraci_obj:
        radek_bunky = []
        for h_sloupec in hraci_obj:
            if h_radek == h_sloupec:
                radek_bunky.append({'typ': 'self' if soutez.typ == '1K' else 'empty'})
            else:
                # Najdeme zápas mezi těmito dvěma hráči
                mozne_zapasy = [z for z in zapasy_v_soutezi if 
                               (z.hrac_domaci_id == h_radek.id and z.hrac_hoste_id == h_sloupec.id) or
                               (z.hrac_domaci_id == h_sloupec.id and z.hrac_hoste_id == h_radek.id)]
                
                z_obj = next((z for z in mozne_zapasy), None)
                vysledek_v_bunce = None

                # Pokud je zápas odehraný, připravíme text skóre
                if z_obj and z_obj.odehrano:
                    if z_obj.hrac_domaci_id == h_radek.id:
                        vysledek_v_bunce = f"{z_obj.sety_domaci}:{z_obj.sety_hoste}"
                    else:
                        vysledek_v_bunce = f"{z_obj.sety_hoste}:{z_obj.sety_domaci}"
                
                # Sestavení URL pro proklik
                if z_obj:
                    u = reverse('editovat_vysledek', args=[z_obj.id])
                else:
                    u = f"{reverse('zadat_vysledek')}?hrac_domaci={h_radek.id}&hrac_hoste={h_sloupec.id}&slug={soutez.slug}"
                
                # TADY JE TO KLÍČOVÉ:
                radek_bunky.append({
                    'typ': 'zapas', 
                    'z': z_obj if (z_obj and z_obj.odehrano) else None, # Pro výsledek
                    'z_obj': z_obj,                                    # Pro tenisák 🎾
                    'vysledek': vysledek_v_bunce, 
                    'url': u
                })
        matice.append({'hrac': h_radek, 'bunky': radek_bunky})

    # 8. Finální návrat dat - TADY BYLA TA CHYBA (přiřazení historie a planovane)
    return {
        'soutez': soutez,
        'hraci': hraci_obj,
        'matice': matice,
        'historie': zobrazit_historii,  # Opraveno
        'planovane': zobrazit_plan,     # Opraveno
        'vybrany_hrac': vybrany_hrac,
        'pismeno': soutez.nazev
    }
# =================================================================
# 2. HLAVNÍ POHLEDY (Views)
# =================================================================

@login_required
def detail_souteze(request, soutez_slug):
    soutez = get_object_or_404(Soutez, slug=soutez_slug)
    context = vypocitej_tabulku_dat(soutez=soutez, request=request)
    
    # Přidáme 'tenis_app/' před název souboru
    if soutez.typ == '2K':
        return render(request, 'tenis_app/dvoukolova_tabulka.html', context)
    else:
        return render(request, 'tenis_app/tabulka_5ti_lig.html', context)
    
    
@login_required
def zadat_vysledek(request):
    soutez_slug = request.GET.get('slug')
    soutez_obj = get_object_or_404(Soutez, slug=soutez_slug)

    if request.method == 'POST':
        form = ZapasForm(request.POST)
        if form.is_valid():
            zapas = form.save(commit=False)
            zapas.soutez = soutez_obj
            zapas.odehrano = True
            if not zapas.datum: zapas.datum = timezone.now().date()
            zapas.save()
            return redirect('detail_souteze', soutez_slug=soutez_obj.slug)
    else:
        form = ZapasForm(initial={
            'hrac_domaci': request.GET.get('hrac_domaci'), 
            'hrac_hoste': request.GET.get('hrac_hoste')
        })
    
    return render(request, 'tenis_app/zadat_vysledek.html', {'form': form, 'soutez': soutez_obj})

# =================================================================
# 3. SPRÁVA (Editace, Mazání)
# =================================================================

@login_required
# views.py

@login_required
def editovat_vysledek(request, pk):
    zapas = get_object_or_404(Zapas, pk=pk)
    
    if request.method == 'POST':
        # Předáme uživatele i do POSTu, aby formulář věděl, že má pole ignorovat
        form = ZapasForm(request.POST, instance=zapas, user=request.user)
        if form.is_valid():
            # ... vaše logika uložení ...
            zapas.save()
            return redirect('detail_souteze', soutez_slug=zapas.soutez.slug)
    else:
        # Předáme uživatele do prázdného formuláře
        form = ZapasForm(instance=zapas, user=request.user)
        
    return render(request, 'tenis_app/editovat_vysledek.html', {'form': form, 'zapas': zapas})
    
    
@login_required
def smazat_vysledek(request, pk):
    zapas = get_object_or_404(Zapas, pk=pk)
    slug = zapas.soutez.slug
    zapas.delete()
    return redirect('detail_souteze', soutez_slug=slug)

@login_required
def pridat_hrace(request):
    if request.method == 'POST':
        form = HracForm(request.POST, request.FILES) # Přidejte request.FILES kvůli fotkám
        if form.is_valid():
            form.save()
            return redirect('tenis_index')
    else:
        form = HracForm() # Žádné initial={'klub': ...}
    return render(request, 'tenis_app/pridat_hrace.html', {'form': form})

@login_required
def editovat_hrace(request, pk):
    hrac = get_object_or_404(Hrac, pk=pk)
    if request.method == 'POST':
        form = HracForm(request.POST, request.FILES, instance=hrac)
        if form.is_valid():
            form.save()
            return redirect('tenis_index')
    else:
        form = HracForm(instance=hrac)
    
    # PŘIDEJTE 'hrac': hrac DO CONTEXTU:
    return render(request, 'tenis_app/editovat_hrace.html', {
        'form': form, 
        'hrac': hrac
    })

@login_required
def smazat_hrace(request, pk):
    hrac = get_object_or_404(Hrac, pk=pk)
    hrac.delete()
    return redirect('tenis_index')

@login_required
def prehled_vsech_zapasu(request):
    # 1. Musíme vzít všechny zápasy
    vsechny = Zapas.objects.all()
    
    # 2. Filtrování podle hráče (pokud je vybrán)
    hrac_id = request.GET.get('filtr_hrac')
    vybrany_hrac = None
    if hrac_id and hrac_id.isdigit():
        vybrany_hrac = get_object_or_404(Hrac, id=hrac_id)
        vsechny = vsechny.filter(Q(hrac_domaci=vybrany_hrac) | Q(hrac_hoste=vybrany_hrac))

    # 3. ROZDĚLENÍ - Tady se láme chleba:
    # Plánované = odehrano je False
    planovane = Zapas.objects.filter(odehrano=False).order_by(F('datum').desc(nulls_last=True))
    # Historie = odehrano je True
    historie = vsechny.filter(odehrano=True).order_by('-datum')

    return render(request, 'tenis_app/vsechny_zapasy.html', {
        'planovane': planovane,
        'historie': historie,
        'vybrany_hrac': vybrany_hrac,
    })
    

from django.db.models import Q  # Ujisti se, že máš tento import nahoře
@login_required
def vsechny_zapasy(request):
    # 1. Základní načtení všech odehraných zápasů
    historie = Zapas.objects.filter(odehrano=True).order_by('-datum', '-id')
    
    # 2. CHYTÁNÍ FILTRU: Podíváme se, jestli v URL není ?filtr_hrac=ID
    hrac_id = request.GET.get('filtr_hrac')
    vybrany_hrac = None
    
    if hrac_id and hrac_id.isdigit():
        vybrany_hrac = get_object_or_404(Hrac, id=hrac_id)
        # Vyfiltrujeme zápasy, kde byl daný hráč buď domácí, nebo host
        historie = historie.filter(Q(hrac_domaci=vybrany_hrac) | Q(hrac_hoste=vybrany_hrac))

    # 3. Předání do šablony
    context = {
        'historie': historie,
        'vybrany_hrac': vybrany_hrac,
        'titulek': 'Všechny odehrané zápasy'
    }
    return render(request, 'tenis_app/vsechny_zapasy.html', context)
    
@login_required    
def tenis_index(request):
    souteze = Soutez.objects.filter(aktivni=True)
    return render(request, 'tenis_app/index.html', {'souteze': souteze})
    
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from .models import Zapas, Soutez
# Importuj logiku ze svých commandů, pokud ji máš ve funkcích, 
# nebo ji sem prostě zkopíruj.

@user_passes_test(lambda u: u.is_superuser)  # Přístup jen pro admina
def admin_tools_view(request):
    if request.method == "POST":
        akce = request.POST.get("akce")
        
        if akce == "opravit_vazby":
            # Tady je ten kód, co jsme psali do shellu
            soutez = Soutez.objects.filter(slug='26_kaminka_leto_D').first()
            if soutez:
                updated = Zapas.objects.filter(soutez__isnull=True).update(soutez=soutez)
                messages.success(request, f"Opraveno {updated} zápasů.")
            else:
                messages.error(request, "Soutěž nenalezena.")
                
        elif akce == "vynutit_migrace":
            # Můžeš volat i management commandy přímo z kódu
            from django.core.management import call_command
            try:
                call_command('migrate', '--fake-initial')
                messages.success(request, "Migrace proběhly (fake-initial).")
            except Exception as e:
                messages.error(request, f"Chyba: {e}")

        return redirect('admin_tools')

    return render(request, 'tenis_app/admin_tools.html')
    
    
    
from django.shortcuts import redirect
from django.contrib import messages
from django.core.management import call_command
from django.contrib.auth.decorators import user_passes_test

@user_passes_test(lambda u: u.is_superuser)
def admin_tools_launcher(request):
    if request.method == "POST":
        akce = request.POST.get("akce")
        
        try:
            if akce == "generovat_ligy":
                # Přidáme Base ligu do seznamu, jak jste chtěl
                ligy_k_uprave = [
                    {'slug': '26_kaminka_leto_base', 'klub': 'Léto 2026 - BASE'}, 
                    {'slug': '26_kaminka_leto_A', 'klub': 'Léto 2026 - A'},
                    {'slug': '26_kaminka_leto_B', 'klub': 'Léto 2026 - B'},
                    {'slug': '26_kaminka_leto_C', 'klub': 'Léto 2026 - C'},
                    {'slug': '26_kaminka_leto_D', 'klub': 'Léto 2026 - D'},
                    {'slug': '26_kaminka_leto_E', 'klub': 'Léto 2026 - E'},
                    {'slug': '26_kaminka_leto_z', 'klub': 'Léto 2026 - Ženy'},
                ]

                celkovy_pocet = 0
                for liga in ligy_k_uprave:
                    # Tady používáme globální Soutez - nesmí se přepsat!
                    soutez_obj = Soutez.objects.filter(slug=liga['slug']).first()
                    hraci = list(Hrac.objects.filter(klub=liga['klub']))
                    
                    if not soutez_obj or not hraci:
                        continue

                    Zapas.objects.filter(soutez=soutez_obj).delete()
                    
                    vsechny_dvojice = []
                    for i in range(len(hraci)):
                        for j in range(i + 1, len(hraci)):
                            vsechny_dvojice.append([hraci[i], hraci[j]])

                    import random # Import raději tady nebo úplně nahoře
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
                            soutez=soutez_obj,
                            hrac_domaci=domaci,
                            hrac_hoste=host,
                            mice_bere_domaci=bere_domaci,
                            odehrano=False,
                            datum='2026-04-26'
                        )
                        celkovy_pocet += 1
                
                messages.success(request, f"🚀 Ligy restartovány! Vygenerováno {celkovy_pocet} vybalancovaných zápasů.")

            # --- OPRAVA TADY: Smazány řádky "from .models import Zapas, Soutez" ---
            
            elif akce == "vytvor_hrace":
                    try:
                        from django.core.management import call_command
                        # Spuštění příkazu a zachycení výstupu
                        call_command('vytvor_hrace')
                        messages.success(request, "✅ Účty byly úspěšně vygenerovány.")
                    except Exception as e:
                        # Pokud se něco pokazí, uvidíte přesně co (např. chyba v importu)
                        messages.error(request, f"❌ Chyba při spouštění skriptu: {str(e)}")
            
            
            
            elif akce == "opravit_vazby":
                s = Soutez.objects.filter(slug='26_kaminka_leto_D').first()
                count = Zapas.objects.filter(soutez__isnull=True).update(soutez=s)
                messages.success(request, f"🚀 Hotovo: {count} zápasů přiřazeno.")
                
            elif akce == "vynutit_migrace":
                call_command('migrate', '--fake-initial')
                messages.success(request, "✅ Migrace proběhly (fake-initial).")

            elif akce == "fix_mice":
                from django.db import connection
                with connection.cursor() as cursor:
                    try:
                        cursor.execute("ALTER TABLE tenis_app_zapas ADD COLUMN mice_bere_domaci bool NOT NULL DEFAULT 1")
                        messages.success(request, "Sloupec pro míče byl úspěšně přidán.")
                    except Exception as e:
                        messages.info(request, f"Sloupec již existuje: {e}")
                            
            elif akce == "smazat_data_zapasu":
                # Tady byl další zbytečný import, smazán.
                count = Zapas.objects.filter(odehrano=False).update(datum=None)
                messages.success(request, f"Vynulováno datum u {count} zápasů.")

        except Exception as e:
            messages.error(request, f"❌ Chyba: {str(e)}")

    return redirect(request.META.get('HTTP_REFERER', '/'))
