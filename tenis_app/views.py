import logging
import random
import unicodedata
from collections import defaultdict
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.core.management import call_command
from django.db.models import F, Q
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone


from zebricek_app.models import ZebricekPozice
from zebricek_app.views import aktualizuj_pozice_zebricku

from .forms import HracForm, ZapasForm
from .models import Hrac, Soutez, Zapas, SystemLog

logger = logging.getLogger(__name__)


# =================================================================
# POMOCNÉ FUNKCE
# =================================================================

def secti_gemy(set_str):
    """Pomocná funkce pro rozpad řetězce setu (např. '6:4') na gemy."""
    if not set_str or ':' not in set_str or set_str == '0:0':
        return 0, 0
    try:
        d, h = map(int, set_str.split(':'))
        return d, h
    except ValueError:
        return 0, 0


from tenis_app.models import Soutez, Hrac, Zapas
from itertools import combinations

def vygeneruj_zapas_pro_soutez(soutez_slug):
    """Centrální funkce pro generování zápasů podle typu soutěže (1K vs 2K)."""
    try:
        soutez = Soutez.objects.get(slug=soutez_slug)
    except Soutez.DoesNotExist:
        return 0

    # 1. Primárně zkusíme načíst hráče podle textového pole 'klub' (shodného s názvem soutěže)
    hraci = list(Hrac.objects.filter(klub=soutez.nazev))
    
    # 2. Pokud by v klubu nikdo nebyl, zkontrolujeme ManyToMany vazbu ('souteze')
    if not hraci:
        hraci = list(Hrac.objects.filter(souteze=soutez))
        
    # 3. Případná stará vazba přes .hraci
    if not hraci and hasattr(soutez, 'hraci'):
        hraci = list(soutez.hraci.all())

    n = len(hraci)
    if n < 2:
        return 0  # Málo hráčů na vygenerování zápasů

    # Bezpečné smazání starých zápasů před novým generováním
    Zapas.objects.filter(soutez=soutez).delete()

    vytvoreno = 0

    # --- JEDNOKOLOVÁ SOUTĚŽ (1K) ---
    if soutez.typ == '1K':
        for idx, (h1, h2) in enumerate(combinations(hraci, 2)):
            bere_domaci = (idx % 2 == 0)

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

                    Zapas.objects.create(
                        soutez=soutez,
                        hrac_domaci=h1,
                        hrac_hoste=h2,
                        mice_bere_domaci=bere_domaci,
                        odehrano=False,
                        datum=None
                    )
                    vytvoreno += 1

    return vytvoreno  
# =================================================================    
# 1. UNIVERZÁLNÍ VÝPOČETNÍ JÁDRO
# =================================================================

def vypocitej_tabulku_dat(soutez, request=None):
    zapasy_v_soutezi = Zapas.objects.filter(soutez=soutez)
    vybrany_hrac = None
    
    id_hracu = set()
    for z in zapasy_v_soutezi:
        id_hracu.add(z.hrac_domaci_id)
        id_hracu.add(z.hrac_hoste_id)
    
    hraci_obj = list(Hrac.objects.filter(id__in=id_hracu))
    if not hraci_obj:
        hraci_obj = list(soutez.hraci.all())

    vsechny_odehrane = zapasy_v_soutezi.filter(odehrano=True).order_by('-datum', '-id')
    planovane_zapasy = zapasy_v_soutezi.filter(odehrano=False).order_by('-datum', 'id')

    zobrazit_historie = vsechny_odehrane
    zobrazit_plan = planovane_zapasy

    if request:
        filtr_hrac_id = request.GET.get('filtr_hrac')
        if filtr_hrac_id and filtr_hrac_id.isdigit():
            vybrany_hrac = Hrac.objects.filter(id=filtr_hrac_id).first()
            if vybrany_hrac:
                zobrazit_historie = vsechny_odehrane.filter(
                    Q(hrac_domaci=vybrany_hrac) | Q(hrac_hoste=vybrany_hrac)
                )
                zobrazit_plan = planovane_zapasy.filter(
                    Q(hrac_domaci=vybrany_hrac) | Q(hrac_hoste=vybrany_hrac)
                )

    for h in hraci_obj:
        h.pocet_bodu, h.s_v, h.s_p = 0, 0, 0
        h.g_v, h.g_p = 0, 0
        
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

            for set_str in [z.set1, z.set2, z.set3]:
                g_d, g_h = secti_gemy(set_str)
                if z.hrac_domaci == h:
                    h.g_v += g_d
                    h.g_p += g_h
                else:
                    h.g_v += g_h
                    h.g_p += g_d

    # Řazení tabulky: 1. Body, 2. Vzájemný zápas, 3. Rozdíl setů, 4. Vyhrané sety
    def vzajemny_zapas_porovnani(h1, h2):
        """Zjistí vzájemný zápas mezi h1 a h2. 
           Vrátí 1, pokud by měl být h1 před h2, -1 pokud h2 před h1, jinak 0."""
        vzajemne = zapasy_v_soutezi.filter(odehrano=True).filter(
            (Q(hrac_domaci=h1) & Q(hrac_hoste=h2)) | (Q(hrac_domaci=h2) & Q(hrac_hoste=h1))
        )
        b1, b2 = 0, 0
        for z in vzajemne:
            bd, bh = z.ziskej_body()
            if z.hrac_domaci == h1:
                b1 += bd
                b2 += bh
            else:
                b1 += bh
                b2 += bd
        
        if b1 > b2:
            return 1   # h1 vyhrál vzájemný zápas -> bude výš
        elif b1 < b2:
            return -1  # h2 vyhrál vzájemný zápas -> bude výš
        return 0       # vzájemný zápas nerozhodl

    from functools import cmp_to_key

    def custom_sort(h1, h2):
        # 1. Celkové body (sestupně -> ten s více body je dřív)
        if h1.pocet_bodu != h2.pocet_bodu:
            return h2.pocet_bodu - h1.pocet_bodu
        
        # 2. Vzájemný zápas (pokud mají stejné body)
        vysledek_vzajemneho = vzajemny_zapas_porovnani(h1, h2)
        if vysledek_vzajemneho != 0:
            return -vysledek_vzajemneho  # záporné znaménko, protože cmp_to_key řadí sestupně
            
        # 3. Rozdíl setů (sestupně)
        rozdil_1 = h1.s_v - h1.s_p
        rozdil_2 = h2.s_v - h2.s_p
        if rozdil_1 != rozdil_2:
            return rozdil_2 - rozdil_1
            
        # 4. Vyhrané sety (sestupně)
        return h2.s_v - h1.s_v

    hraci_obj.sort(key=cmp_to_key(custom_sort))

    # Křížová tabulka
    matice = []
    for h_radek in hraci_obj:
        radek_bunky = []
        for h_sloupec in hraci_obj:
            if h_radek == h_sloupec:
                radek_bunky.append({'typ': 'self' if soutez.typ == '1K' else 'empty'})
            else:
                mozne_zapasy = [z for z in zapasy_v_soutezi if 
                    (z.hrac_domaci_id == h_radek.id and z.hrac_hoste_id == h_sloupec.id) or
                    (z.hrac_domaci_id == h_sloupec.id and z.hrac_hoste_id == h_radek.id)]
                
                z1, z2 = None, None
                url1, url2 = None, None
                z_obj = None
                vysledek_v_bunce = None

                if soutez.typ == '1K':
                    if mozne_zapasy:
                        z1 = mozne_zapasy[0]
                        z_obj = z1
                    
                    if not z1:
                        url1 = f"{reverse('tenis_app:zadat_vysledek')}?hrac_domaci={h_radek.id}&hrac_hoste={h_sloupec.id}&slug={soutez.slug}"
                    else:
                        url1 = reverse('tenis_app:editovat_vysledek', args=[z1.id])
                else:
                    z1 = next((z for z in mozne_zapasy if z.hrac_domaci_id == h_radek.id), None)
                    z2 = next((z for z in mozne_zapasy if z.hrac_hoste_id == h_radek.id), None)

                    if not z1:
                        url1 = f"{reverse('tenis_app:zadat_vysledek')}?hrac_domaci={h_radek.id}&hrac_hoste={h_sloupec.id}&slug={soutez.slug}"
                    if not z2:
                        url2 = f"{reverse('tenis_app:zadat_vysledek')}?hrac_domaci={h_sloupec.id}&hrac_hoste={h_radek.id}&slug={soutez.slug}"

                if z_obj and z_obj.odehrano:
                    if z_obj.hrac_domaci_id == h_radek.id:
                        vysledek_v_bunce = f"{z_obj.sety_domaci}:{z_obj.sety_hoste}"
                    else:
                        vysledek_v_bunce = f"{z_obj.sety_hoste}:{z_obj.sety_domaci}"

                radek_bunky.append({
                    'typ': 'zapas', 
                    'z1': z1,
                    'z2': z2,
                    'url1': url1,
                    'url2': url2,
                    'z': z_obj if (z_obj and z_obj.odehrano) else None,
                    'z_obj': z_obj,
                    'vysledek': vysledek_v_bunce,
                    'url': url1
                })
        matice.append({'hrac': h_radek, 'bunky': radek_bunky})

    return {
        'soutez': soutez,
        'hraci': hraci_obj,
        'matice': matice,
        'historie': zobrazit_historie,
        'planovane': zobrazit_plan,
        'vybrany_hrac': vybrany_hrac,
        'pismeno': soutez.nazev
    }


# =================================================================
# 2. HLAVNÍ UŽIVATELSKÉ POHLEDY (Views)
# =================================================================

def tenis_index(request):
    """Hlavní strana s odpočtem a přehledem odehranosti lig."""
    konec_ligy = date(2026, 9, 19)
    dnes = date.today()
    dni_do_konce = max((konec_ligy - dnes).days, 0)

    aktivni_souteze = Soutez.objects.filter(nazev__icontains="2026", aktivni=True)
    
    ligy_statistiky = []
    souteze_k_zapoctu = []

    for soutez in aktivni_souteze:
        nazev_lower = soutez.nazev.lower()
        slug_lower = soutez.slug.lower()

        if "zebricek" in slug_lower or "mix" in nazev_lower:
            continue

        souteze_k_zapoctu.append(soutez)
        soutez_zapasu = Zapas.objects.filter(soutez=soutez)
        
        ligy_statistiky.append({
            'nazev': soutez.nazev,
            'odehrano': soutez_zapasu.filter(odehrano=True).count(),
            'zbyva': soutez_zapasu.filter(odehrano=False).count()
        })

    celkem_odehrano = Zapas.objects.filter(soutez__in=souteze_k_zapoctu, odehrano=True).count()
    celkem_zbyva = Zapas.objects.filter(soutez__in=souteze_k_zapoctu, odehrano=False).count()

    context = {
        'dni_do_konce': dni_do_konce,
        'celkem_odehrano': celkem_odehrano,
        'celkem_zbyva': celkem_zbyva,
        'ligy_statistiky': ligy_statistiky,
    }
    return render(request, 'index.html', context)


@login_required
def detail_souteze(request, soutez_slug):
    soutez = get_object_or_404(Soutez, slug=soutez_slug)
    logger.info(f"Uživatel {request.user.username} si prohlíží soutěž: {soutez.nazev}")
    
    context = vypocitej_tabulku_dat(soutez=soutez, request=request)
    
    zapas_stats = Zapas.objects.filter(
        soutez=soutez,
        odehrano=True
    ).select_related('hrac_domaci', 'hrac_hoste')

    data_hracu = defaultdict(lambda: {
        'pocet_zapasu': 0, 
        'body': 0, 
        'sety_ziskane': 0, 
        'sety_ztracene': 0,
        'gemy_ziskane': 0, 
        'gemy_ztracene': 0, 
        'rozdil_gemu': 0,
        'v2_0': 0, 'v2_1': 0,
        'p1_2': 0, 'p0_2': 0,
        'hrac_obj': None
    })

    hraci_v_soutezi = context.get('hraci', [])
    if not hraci_v_soutezi:
        try:
            hraci_v_soutezi = soutez.hraci.all()
        except AttributeError:
            hraci_v_soutezi = []

    for h in hraci_v_soutezi:
        data_hracu[h.id]['hrac_obj'] = h

    for zapas in zapas_stats:
        d_id = zapas.hrac_domaci.id
        h_id = zapas.hrac_hoste.id
        
        if not data_hracu[d_id]['hrac_obj']:
            data_hracu[d_id]['hrac_obj'] = zapas.hrac_domaci
        if not data_hracu[h_id]['hrac_obj']:
            data_hracu[h_id]['hrac_obj'] = zapas.hrac_hoste
        
        data_hracu[d_id]['pocet_zapasu'] += 1
        data_hracu[h_id]['pocet_zapasu'] += 1
        
        if zapas.sety_domaci == 2 and zapas.sety_hoste == 0:
            data_hracu[d_id]['body'] += 3
            data_hracu[d_id]['v2_0'] += 1
            data_hracu[h_id]['p0_2'] += 1
        elif zapas.sety_domaci == 2 and zapas.sety_hoste == 1:
            data_hracu[d_id]['body'] += 2
            data_hracu[h_id]['body'] += 1
            data_hracu[d_id]['v2_1'] += 1
            data_hracu[h_id]['p1_2'] += 1
        elif zapas.sety_domaci == 1 and zapas.sety_hoste == 2:
            data_hracu[d_id]['body'] += 1
            data_hracu[h_id]['body'] += 2
            data_hracu[d_id]['p1_2'] += 1
            data_hracu[h_id]['v2_1'] += 1
        elif zapas.sety_domaci == 0 and zapas.sety_hoste == 2:
            data_hracu[h_id]['body'] += 3
            data_hracu[d_id]['p0_2'] += 1
            data_hracu[h_id]['v2_0'] += 1
            
        data_hracu[d_id]['sety_ziskane'] += zapas.sety_domaci
        data_hracu[d_id]['sety_ztracene'] += zapas.sety_hoste
        data_hracu[h_id]['sety_ziskane'] += zapas.sety_hoste
        data_hracu[h_id]['sety_ztracene'] += zapas.sety_domaci
        
        for set_pole in [zapas.set1, zapas.set2, zapas.set3]:
            g_d, g_h = secti_gemy(set_pole)
            data_hracu[d_id]['gemy_ziskane'] += g_d
            data_hracu[d_id]['gemy_ztracene'] += g_h
            data_hracu[h_id]['gemy_ziskane'] += g_h
            data_hracu[h_id]['gemy_ztracene'] += g_d

    for h_id in data_hracu:
        data_hracu[h_id]['rozdil_gemu'] = data_hracu[h_id]['gemy_ziskane'] - data_hracu[h_id]['gemy_ztracene']

    statistiky_ligy = list(data_hracu.values())
    statistiky_ligy.sort(
        key=lambda x: (
            x['body'],
            (x['sety_ziskane'] - x['sety_ztracene']),
            (x['gemy_ziskane'] - x['gemy_ztracene'])
        ),
        reverse=True
    )

    if 'matice' in context:
        for radek in context['matice']:
            hrac_obj = radek.get('hrac') if isinstance(radek, dict) else getattr(radek, 'hrac', None)
            if hrac_obj and hrac_obj.id in data_hracu:
                stats = data_hracu[hrac_obj.id]
                radek['pocet_zapasu'] = stats['pocet_zapasu']
                radek['body'] = stats['body']
                radek['sety_ziskane'] = stats['sety_ziskane']
                radek['sety_ztracene'] = stats['sety_ztracene']
                radek['gemy_ziskane'] = stats['gemy_ziskane']
                radek['gemy_ztracene'] = stats['gemy_ztracene']

    # --- SPOČÍTÁNÍ MÍČKŮ V PLÁNU PRO KAŽDÉHO HRÁČE ---
    planovane_zapasy = context.get('planovane', [])
    for hrac in hraci_v_soutezi:
        pocet = 0
        for zapas in planovane_zapasy:
            # Pokud je hráč domácí a bere míče domácí
            if zapas.hrac_domaci_id == hrac.id and getattr(zapas, 'mice_bere_domaci', True):
                pocet += 1
            # Pokud je hráč hostující a míče bere host
            elif zapas.hrac_hoste_id == hrac.id and not getattr(zapas, 'mice_bere_domaci', True):
                pocet += 1
        hrac.pocet_micku_v_planu = pocet

    context['statistiky_ligy'] = statistiky_ligy

    if soutez.typ == '2K':
        return render(request, 'tenis_app/dvoukolova_tabulka.html', context)
    return render(request, 'tenis_app/tabulka_5ti_lig.html', context)

@login_required
def zadat_vysledek(request):
    hrac_domaci_id = request.GET.get('hrac_domaci')
    hrac_hoste_id = request.GET.get('hrac_hoste')
    soutez_slug = request.GET.get('soutez') or request.GET.get('slug')

    soutez_obj = Soutez.objects.filter(slug=soutez_slug).first() if soutez_slug else Soutez.objects.first()
    if not soutez_obj:
        return HttpResponse("V databázi neexistuje žádná soutěž.")

    if request.method == 'POST':
        form = ZapasForm(request.POST)
        if form.is_valid():
            zapas = form.save(commit=False)
            zapas.soutez = soutez_obj
            zapas.odehrano = True
            
            if not zapas.datum: 
                zapas.datum = timezone.now().date()
            
            zapas.sety_domaci = 0
            zapas.sety_hoste = 0
            for s in [zapas.set1, zapas.set2, zapas.set3]:
                if s and ':' in s and s != '0:0':
                    d, h = map(int, s.split(':'))
                    if d > h: zapas.sety_domaci += 1
                    elif h > d: zapas.sety_hoste += 1

            zapas.save()
            logger.info(f"VÝSLEDEK ZAPSÁN: {zapas.hrac_domaci} vs {zapas.hrac_hoste} - {zapas.set1}")

            aktualizuj_pozice_zebricku(zapas)
            return redirect('zebricek_app:zebricek_index')
    else:
        form = ZapasForm(initial={
            'hrac_domaci': hrac_domaci_id, 
            'hrac_hoste': hrac_hoste_id
        })
    
    return render(request, 'tenis_app/zadat_vysledek.html', {'form': form, 'soutez': soutez_obj})


@login_required
def prehled_vsech_zapasu(request):
    """Přehled zápasů a celkových statistik pro sezónu Léto 2026."""
    vsechny = Zapas.objects.all()
    
    hrac_id = request.GET.get('filtr_hrac')
    vybrany_hrac = None
    if hrac_id and hrac_id.isdigit():
        vybrany_hrac = get_object_or_404(Hrac, id=hrac_id)
        vsechny = vsechny.filter(Q(hrac_domaci=vybrany_hrac) | Q(hrac_hoste=vybrany_hrac))

    planovane = Zapas.objects.filter(odehrano=False).order_by(F('datum').desc(nulls_last=True))
    historie = vsechny.filter(odehrano=True).order_by('-datum')

    zapas_stats = Zapas.objects.filter(
        odehrano=True,
        soutez__slug__startswith='26_'
    ).exclude(
        Q(soutez__slug__icontains='zebricek') | Q(soutez__slug__icontains='zima')
    ).select_related('hrac_domaci', 'hrac_hoste')

    data_hracu = defaultdict(lambda: {
        'pocet_zapasu': 0, 
        'body': 0, 
        'sety_ziskane': 0, 
        'sety_ztracene': 0,
        'gemy_ziskane': 0, 
        'gemy_ztracene': 0, 
        'rozdil_gemu': 0,
        'v2_0': 0, 'v2_1': 0,
        'p1_2': 0, 'p0_2': 0,
        'hrac_obj': None
    })

    for h in Hrac.objects.all():
        data_hracu[h.id]['hrac_obj'] = h

    for zapas in zapas_stats:
        d_id = zapas.hrac_domaci.id
        h_id = zapas.hrac_hoste.id
        
        data_hracu[d_id]['pocet_zapasu'] += 1
        data_hracu[h_id]['pocet_zapasu'] += 1
        
        if zapas.sety_domaci == 2 and zapas.sety_hoste == 0:
            data_hracu[d_id]['body'] += 3
            data_hracu[d_id]['v2_0'] += 1
            data_hracu[h_id]['p0_2'] += 1
        elif zapas.sety_domaci == 2 and zapas.sety_hoste == 1:
            data_hracu[d_id]['body'] += 2
            data_hracu[h_id]['body'] += 1
            data_hracu[d_id]['v2_1'] += 1
            data_hracu[h_id]['p1_2'] += 1
        elif zapas.sety_domaci == 1 and zapas.sety_hoste == 2:
            data_hracu[d_id]['body'] += 1
            data_hracu[h_id]['body'] += 2
            data_hracu[d_id]['p1_2'] += 1
            data_hracu[h_id]['v2_1'] += 1
        elif zapas.sety_domaci == 0 and zapas.sety_hoste == 2:
            data_hracu[h_id]['body'] += 3
            data_hracu[d_id]['p0_2'] += 1
            data_hracu[h_id]['v2_0'] += 1
            
        data_hracu[d_id]['sety_ziskane'] += zapas.sety_domaci
        data_hracu[d_id]['sety_ztracene'] += zapas.sety_hoste
        data_hracu[h_id]['sety_ziskane'] += zapas.sety_hoste
        data_hracu[h_id]['sety_ztracene'] += zapas.sety_domaci
        
        for set_pole in [zapas.set1, zapas.set2, zapas.set3]:
            g_d, g_h = secti_gemy(set_pole)
            data_hracu[d_id]['gemy_ziskane'] += g_d
            data_hracu[d_id]['gemy_ztracene'] += g_h
            data_hracu[h_id]['gemy_ziskane'] += g_h
            data_hracu[h_id]['gemy_ztracene'] += g_d

    for h_id in data_hracu:
        data_hracu[h_id]['rozdil_gemu'] = data_hracu[h_id]['gemy_ziskane'] - data_hracu[h_id]['gemy_ztracene']

    statistiky_hracu = list(data_hracu.values())
    statistiky_hracu.sort(
        key=lambda x: (x['pocet_zapasu'], x['body'], x['rozdil_gemu']), 
        reverse=True
    )

    return render(request, 'tenis_app/vsechny_zapasy.html', {
        'planovane': planovane,
        'historie': historie,
        'vybrany_hrac': vybrany_hrac,
        'statistiky_hracu': statistiky_hracu,
    })


# =================================================================
# 3. SPRÁVA ZÁPASŮ A HRÁČŮ
# =================================================================
@login_required
def editovat_vysledek(request, pk):
    zapas = get_object_or_404(Zapas, id=pk)
    
    ma_opravneni = (
        zapas.hrac_domaci.ma_pristup(request.user) or 
        zapas.hrac_hoste.ma_pristup(request.user)
    )
    
    if not ma_opravneni and not request.user.is_staff:
        messages.error(request, "Nemůžeš editovat zápas, kterého jsi se neúčastnil.")
        return redirect('tenis_app:detail_souteze', soutez_slug=zapas.soutez.slug)
   
    if request.method == 'POST':
        # Získáme vrácenou URL ze skrytého pole formuláře
        navratova_url = request.POST.get('next')
        if not navratova_url:
            navratova_url = reverse('tenis_app:detail_souteze', args=[zapas.soutez.slug])

        # Schováme si původní datum a skóre
        puvodni_datum = zapas.datum
        stary_sety_d = zapas.sety_domaci
        stary_sety_h = zapas.sety_hoste
        stary_s1 = zapas.set1 or ''
        stary_s2 = zapas.set2 or ''
        stary_s3 = zapas.set3 or ''
        
        form = ZapasForm(request.POST, instance=zapas, user=request.user)
        if form.is_valid():
            zapas_obj = form.save(commit=False)
            
            # Zjistíme, zda uživatel výslovně vymazal datum ve formuláři
            vymazal_datum = 'datum' in request.POST and not request.POST.get('datum')

            # Určení stavu odehráno
            je_odehrano = (zapas_obj.sety_domaci is not None and zapas_obj.sety_hoste is not None)
            
            if je_odehrano:
                zapas_obj.odehrano = True
                if not zapas_obj.datum and not vymazal_datum:
                    zapas_obj.datum = timezone.now().date()
            else:
                zapas_obj.odehrano = False
            
            if vymazal_datum:
                zapas_obj.datum = None
                
            zapas_obj.save()
            
            if je_odehrano:
                stary_text = f"{stary_sety_d}:{stary_sety_h} ({stary_s1}, {stary_s2}, {stary_s3})"
                novy_text = f"{zapas_obj.sety_domaci}:{zapas_obj.sety_hoste} ({zapas_obj.set1 or ''}, {zapas_obj.set2 or ''}, {zapas_obj.set3 or ''})"
                
                # Formátování původního a nového data pro log
                puvodni_datum_str = puvodni_datum.strftime('%d.%m.%Y') if puvodni_datum else 'neurčeno'
                nove_datum_str = zapas_obj.datum.strftime('%d.%m.%Y') if zapas_obj.datum else 'neurčeno'

                SystemLog.write(
                    message=f"Byl upraven výsledek zápasu: <strong>{zapas_obj.hrac_domaci} vs {zapas_obj.hrac_hoste}</strong><br>"
                            f"<span class='text-muted'>Původní:</span> {stary_text} <span class='text-muted'>(termín: {puvodni_datum_str})</span><br>"
                            f"<span class='text-success'>Nový:</span> <strong>{novy_text}</strong> <span class='text-success'>(termín: {nove_datum_str})</span>",
                    user=request.user,
                    source="Zápasy"
                )
                messages.success(request, "Výsledek byl úspěšně uložen.")
                
            # Správný návrat tam, odkud uživatel přišel
            return redirect(navratova_url)
        else:
            messages.error(request, f"Chyba při uložení: {form.errors}")
    else:
        # PŘI ZOBRAZENÍ FORMULÁŘE zachytíme, odkud uživatel přišel
        navratova_url = request.META.get('HTTP_REFERER')
        if not navratova_url:
            navratova_url = reverse('tenis_app:detail_souteze', args=[zapas.soutez.slug])

        initial_data = {}
        if zapas.datum:
            initial_data['datum'] = zapas.datum.strftime('%Y-%m-%d')
            
        form = ZapasForm(instance=zapas, user=request.user, initial=initial_data)
        
    return render(request, 'tenis_app/editovat_vysledek.html', {
        'form': form, 
        'zapas': zapas,
        'navratova_url': navratova_url
    })
    
    

@login_required
def smazat_vysledek(request, pk):
    zapas = get_object_or_404(Zapas, id=pk)
    
    je_ucastnik = (request.user == zapas.hrac_domaci.user or request.user == zapas.hrac_hoste.user)
    if not je_ucastnik and not request.user.is_staff:
        messages.error(request, "Nemáš oprávnění smazat tento výsledek.")
        return redirect('zebricek_app:zebricek_index')

    if request.method == 'POST':
        zapas.delete()
        messages.success(request, "Výsledek byl úspěšně smazán.")
        return redirect('zebricek_app:zebricek_index')

    context = {
        'zapas': zapas,
        'objekt': f"{zapas.hrac_domaci} vs {zapas.hrac_hoste}",
        'zpet_url_name': 'zebricek_app:zebricek_index',
    }
    return render(request, 'tenis_app/potvrdit_smazani.html', context)


@login_required
def pridat_hrace(request):
    if request.method == 'POST':
        form = HracForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('tenis_app:hraci_prehled')
    else:
        form = HracForm()
    return render(request, 'tenis_app/pridat_hrace.html', {'form': form})


@login_required
def editovat_hrace(request, pk):
    hrac = get_object_or_404(Hrac, id=pk)

    if hrac.user != request.user and not request.user.is_staff:
        messages.error(request, "Nemáte oprávnění upravovat tento profil.")
        return redirect('tenis_app:hraci_prehled')

    if request.method == 'POST':
        form = HracForm(request.POST, request.FILES, instance=hrac)
        if form.is_valid():
            form.save()
            messages.success(request, f"Profil hráče {hrac.jmeno} byl aktualizován.")
            return redirect('tenis_app:hraci_prehled')
    else:
        form = HracForm(instance=hrac)

    return render(request, 'tenis_app/editovat_hrace.html', {'form': form, 'hrac': hrac})


@login_required
def smazat_hrace(request, pk):
    hrac = get_object_or_404(Hrac, pk=pk)
    hrac.delete()
    return redirect('tenis_app:hraci_prehled')


def hraci_prehled(request):
    zimni_slugy = ['27_kaminka_zima_A', '27_kaminka_zima_B', '27_kaminka_zima_C', '27_kaminka_zima_D']
    
    zimni_souteze_dict = {
        'zima_a': Soutez.objects.filter(slug='27_kaminka_zima_A').first(),
        'zima_b': Soutez.objects.filter(slug='27_kaminka_zima_B').first(),
        'zima_c': Soutez.objects.filter(slug='27_kaminka_zima_C').first(),
        'zima_d': Soutez.objects.filter(slug='27_kaminka_zima_D').first(),
    }
    
    if request.method == "POST":
        hraci = Hrac.objects.all()
        for hrac in hraci:
            for slug in zimni_slugy:
                soutez = Soutez.objects.filter(slug=slug).first()
                if not soutez:
                    continue
                
                checkbox_name = f"hrac_{hrac.id}_{slug}"
                is_checked = checkbox_name in request.POST
                
                if is_checked and not hrac.souteze.filter(slug=slug).exists():
                    hrac.souteze.add(soutez)
                elif not is_checked and hrac.souteze.filter(slug=slug).exists():
                    hrac.souteze.remove(soutez)
                    
        messages.success(request, "Rozlosování zimních lig bylo úspěšně uloženo.")
        return redirect('tenis_app:hraci_prehled')

    hraci = Hrac.objects.prefetch_related('souteze').all().order_by('klub', 'jmeno')
    for hrac in hraci:
        hrac.soutez_ids_list = list(hrac.souteze.values_list('id', flat=True))
    
    context = {
        'hraci': hraci,
        'zimni_souteze_dict': zimni_souteze_dict,
    }
    return render(request, 'tenis_app/hraci_prehled.html', context)


# =================================================================
# 4. ADMIN NÁSTROJE
# =================================================================

@user_passes_test(lambda u: u.is_superuser)
def admin_tools_view(request):
    """Společné rozhraní pro administrátorské akce."""
    if request.method == "POST":
        akce = request.POST.get("akce")
        
        try:
            if akce == "generovat_jednu_ligu":
                soutez_identifier = request.POST.get("soutez_id") or request.POST.get("slug_ligy")
                
                if soutez_identifier:
                    if soutez_identifier.isdigit():
                        soutez_obj = Soutez.objects.filter(id=int(soutez_identifier)).first()
                    else:
                        soutez_obj = Soutez.objects.filter(slug=soutez_identifier).first()

                    if soutez_obj:
                        # TADY VOLÁME NAŠI JEDNOTNOU CENTRÁLNÍ FUNKCI MÍSTO call_command
                        vytvoreno = vygeneruj_zapas_pro_soutez(soutez_obj.slug)
                        messages.success(request, f"Soutěž '{soutez_obj.nazev}' byla úspěšně vygenerována (vytvořeno {vytvoreno} zápasů).")
                    else:
                        messages.error(request, "Vybraná soutěž neexistuje v databázi.")
                else:
                    messages.warning(request, "Nebyla vybrána žádná soutěž.")

            elif akce == "generovat_ligy":
                # Hromadné generování pro VŠECHNY soutěže přes centrální funkci
                vsechny_souteze = Soutez.objects.all()
                celkovy_pocet = 0

                for soutez_obj in vsechny_souteze:
                    # Každou soutěž vygenerujeme pomocí naší centrální logiky, která respektuje 1K/2K
                    pocet = vygeneruj_zapas_pro_soutez(soutez_obj.slug)
                    celkovy_pocet += pocet
                
                messages.success(request, f"🚀 Všechny ligy byly úspěšně přegenerovány! Celkem vytvořeno {celkovy_pocet} zápasů.")

            elif akce == "parovat_hrace_uzivatele":
                import random
                import string
                from django.contrib.auth.models import User
                from django.utils.text import slugify

                # Vybereme pouze hráče, kteří ještě nemají přiřazený uživatelský účet (pole 'user')
                hraci_bez_uzivatele = Hrac.objects.filter(user__isnull=True)
                upraveno = 0
                
                for hrac in hraci_bez_uzivatele:
                    if not hrac.jmeno:
                        continue

                    # Základní username z jména hráče
                    username = slugify(hrac.jmeno)
                    base_username = username
                    counter = 1
                    # Ošetření, aby username v DB bylo unikátní
                    while User.objects.filter(username=username).exists():
                        username = f"{base_username}{counter}"
                        counter += 1

                    # Vygenerování 5místného hesla
                    heslo = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
                    
                    # Vytvoření nového uživatele v Django
                    user = User.objects.create_user(username=username, password=heslo)
                    
                    # Propojení s hráčem přes pole 'user' a zápis údajů do info
                    hrac.user = user
                    hrac.info = f"Login: {username} | Heslo: {heslo}"
                    hrac.save()
                    upraveno += 1

                messages.success(request, f"🔗 Úspěšně vytvořeny a přiřazeny účty pro {upraveno} nových hráčů (hráči s již přiřazeným účtem byli vynecháni).")

        except Exception as e:
            logger.error(f"Chyba při admin akci '{akce}': {e}")
            messages.error(request, f"❌ Chyba: {str(e)}")

        return redirect(request.META.get('HTTP_REFERER', 'tenis_app:admin_tools'))

    souteze = Soutez.objects.all().order_by('nazev')
    return render(request, 'tenis_app/admin_tools.html', {'souteze': souteze})
    
    
from datetime import date
from .models import Zapas

from datetime import date
from django.db.models import Q, F
from django.shortcuts import render, get_object_or_404
from collections import defaultdict
from .models import Zapas, Hrac

@login_required
def prehled_aktualnich_zapasu(request):
    """Přehled zápasů a statistik pro zimu od 15.10.2026."""
    datum_limit = date(2026, 10, 11)
    
    # Základní queryset pro historii od 15.10.2026
    vsechny = Zapas.objects.filter(datum__gte=datum_limit)
    
    hrac_id = request.GET.get('filtr_hrac')
    vybrany_hrac = None
    if hrac_id and hrac_id.isdigit():
        vybrany_hrac = get_object_or_404(Hrac, id=hrac_id)
        vsechny = vsechny.filter(Q(hrac_domaci=vybrany_hrac) | Q(hrac_hoste=vybrany_hrac))

    planovane = Zapas.objects.filter(datum__gte=datum_limit, odehrano=False).order_by(F('datum').desc(nulls_last=True))
    historie = vsechny.filter(odehrano=True).order_by('-datum')

    # TADY JE KLÍČOVÁ ÚPRAVA: Zápasy pro statistiky omezené od 15.10.2026
    zapas_stats = Zapas.objects.filter(
        odehrano=True,
        datum__gte=datum_limit
    ).select_related('hrac_domaci', 'hrac_hoste')

    data_hracu = defaultdict(lambda: {
        'pocet_zapasu': 0, 
        'body': 0, 
        'sety_ziskane': 0, 
        'sety_ztracene': 0,
        'gemy_ziskane': 0, 
        'gemy_ztracene': 0, 
        'rozdil_gemu': 0,
        'v2_0': 0, 'v2_1': 0,
        'p1_2': 0, 'p0_2': 0,
        'hrac_obj': None
    })

    for h in Hrac.objects.all():
        data_hracu[h.id]['hrac_obj'] = h

    for zapas in zapas_stats:
        d_id = zapas.hrac_domaci.id
        h_id = zapas.hrac_hoste.id
        
        data_hracu[d_id]['pocet_zapasu'] += 1
        data_hracu[h_id]['pocet_zapasu'] += 1
        
        if zapas.sety_domaci == 2 and zapas.sety_hoste == 0:
            data_hracu[d_id]['body'] += 3
            data_hracu[d_id]['v2_0'] += 1
            data_hracu[h_id]['p0_2'] += 1
        elif zapas.sety_domaci == 2 and zapas.sety_hoste == 1:
            data_hracu[d_id]['body'] += 2
            data_hracu[h_id]['body'] += 1
            data_hracu[d_id]['v2_1'] += 1
            data_hracu[h_id]['p1_2'] += 1
        elif zapas.sety_domaci == 1 and zapas.sety_hoste == 2:
            data_hracu[d_id]['body'] += 1
            data_hracu[h_id]['body'] += 2
            data_hracu[d_id]['p1_2'] += 1
            data_hracu[h_id]['v2_1'] += 1
        elif zapas.sety_domaci == 0 and zapas.sety_hoste == 2:
            data_hracu[h_id]['body'] += 3
            data_hracu[d_id]['p0_2'] += 1
            data_hracu[h_id]['v2_0'] += 1
            
        data_hracu[d_id]['sety_ziskane'] += zapas.sety_domaci
        data_hracu[d_id]['sety_ztracene'] += zapas.sety_hoste
        data_hracu[h_id]['sety_ziskane'] += zapas.sety_hoste
        data_hracu[h_id]['sety_ztracene'] += zapas.sety_domaci
        
        for set_pole in [zapas.set1, zapas.set2, zapas.set3]:
            g_d, g_h = secti_gemy(set_pole)
            data_hracu[d_id]['gemy_ziskane'] += g_d
            data_hracu[d_id]['gemy_ztracene'] += g_h
            data_hracu[h_id]['gemy_ziskane'] += g_h
            data_hracu[h_id]['gemy_ztracene'] += g_d

    for h_id in data_hracu:
        data_hracu[h_id]['rozdil_gemu'] = data_hracu[h_id]['gemy_ziskane'] - data_hracu[h_id]['gemy_ztracene']

    statistiky_hracu = list(data_hracu.values())
    statistiky_hracu.sort(
        key=lambda x: (x['pocet_zapasu'], x['body'], x['rozdil_gemu']), 
        reverse=True
    )

    return render(request, 'tenis_app/aktualni_zapasy.html', {
        'planovane': planovane,
        'historie': historie,
        'vybrany_hrac': vybrany_hrac,
        'statistiky_hracu': statistiky_hracu,
    })
    
from .models import Hrac, Soutez

from .models import Hrac, Soutez

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Hrac, Soutez

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Hrac, Soutez

def hraci_prehled(request):
    vsechny_souteze = Soutez.objects.all()
    vsechny_kluby = list(Hrac.objects.exclude(klub__isnull=True).exclude(klub='').values_list('klub', flat=True).distinct().order_by('klub'))

    if request.method == 'POST':
        for hrac in Hrac.objects.all():
            # 1. Uložení soutěží (ManyToManyField)
            aktivni_souteze_ids = []
            for soutez in vsechny_souteze:
                if request.POST.get(f"hrac_{hrac.id}_soutez_{soutez.id}") == '1':
                    aktivni_souteze_ids.append(soutez.id)
            hrac.souteze.set(aktivni_souteze_ids)
            
            # 2. Uložení klubu (CharField - vybírá se přes radio tlačítko)
            vybrany_klub_form = request.POST.get(f"hrac_{hrac.id}_klub")
            if vybrany_klub_form is not None:
                hrac.klub = vybrany_klub_form if vybrany_klub_form != '__none__' else ''
                hrac.save()
                
        messages.success(request, "Změny v klubech a soutěžích byly úspěšně uloženy.")
        return redirect('tenis_app:hraci_prehled')

    # Načtení dat pro zobrazení
    hraci = Hrac.objects.prefetch_related('souteze').all()
    
    vybrany_klub = request.GET.get('klub')
    soutez_id = request.GET.get('soutez')
    
    if vybrany_klub:
        hraci = hraci.filter(klub=vybrany_klub)
        
    vybrana_soutez = None
    if soutez_id and soutez_id.isdigit():
        hraci = hraci.filter(souteze__id=soutez_id)
        vybrana_soutez = Soutez.objects.filter(id=soutez_id).first()

    recent_logs = SystemLog.objects.all()[:15]  # posledních 15 záznamů

    context = {
        'hraci': hraci,
        'vybrany_klub': vybrany_klub,
        'vybrana_soutez': vybrana_soutez,
        'vsechny_souteze': vsechny_souteze,
        'vsechny_kluby': vsechny_kluby,
        'recent_logs': recent_logs,
    }
    return render(request, 'tenis_app/hraci_prehled.html', context)



from collections import defaultdict
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Q
from .models import Hrac, Zapas


from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Q, F
from collections import defaultdict

@login_required
def moje_zapasy_view(request):
    """Osobní stránka přihlášeného hráče s rozdělením zápasů podle lig (včetně podpory pro druhe_user)."""
    
    # 1. Najdeme všechny hráče, ke kterým má přihlášený uživatel přístup (jako primární nebo druhý uživatel)
    pristupni_hraci = Hrac.objects.filter(
        Q(user=request.user) | Q(druhy_user=request.user)
    ).distinct()

    if not pristupni_hraci.exists():
        return render(request, 'tenis_app/moje_zapasy.html', {'hrac': None})

    # Pro zobrazení jména v nadpisu vezmeme prvního nalezeného hráče (nebo můžete přizpůsobit)
    hrac = pristupni_hraci.first()

    # 2. Načteme všechny zápasy, kde DOMÁCÍ nebo HOST PATŘÍ do seznamu přístupných hráčů
    zapasy_hrace = Zapas.objects.filter(
        Q(hrac_domaci__in=pristupni_hraci) | Q(hrac_hoste__in=pristupni_hraci)
    ).select_related('hrac_domaci', 'hrac_hoste', 'soutez')

    # Plánované zápasy
    planovane_list = zapasy_hrace.filter(odehrano=False).order_by(
        'soutez__nazev', 
        F('datum').asc(nulls_last=True), 
        'id'
    )
    
    # Odehrané zápasy
    historie_list = zapasy_hrace.filter(odehrano=True).order_by(
        'soutez__nazev', 
        F('datum').desc(nulls_last=True), 
        '-id'
    )

    # Seskupení plánovaných podle soutěže
    planovane_by_soutez = defaultdict(list)
    for z in planovane_list:
        planovane_by_soutez[z.soutez].append(z)

    # Seskupení historie podle soutěže
    historie_by_soutez = defaultdict(list)
    for z in historie_list:
        historie_by_soutez[z.soutez].append(z)

    context = {
        'hrac': hrac,
        'planovane_by_soutez': dict(planovane_by_soutez),
        'historie_by_soutez': dict(historie_by_soutez),
        'celkem_planovane': planovane_list.count(),
        'celkem_historie': historie_list.count(),
    }
    return render(request, 'tenis_app/moje_zapasy.html', context)