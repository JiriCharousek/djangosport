from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.urls import reverse
from .models import Hrac, Zapas, Soutez
from .forms import HracForm, ZapasForm
from django.contrib.auth.decorators import login_required
# =================================================================
# 1. UNIVERZÁLNÍ VÝPOČETNÍ JÁDRO (Modulární systém)
# =================================================================


def vypocitej_tabulku_dat(soutez, request=None):
    # 1. Základní queryset zápasů této soutěže
    zapasy_v_soutezi = Zapas.objects.filter(soutez=soutez)
    
    # Inicializace vybrany_hrac hned na začátku, aby nebyl UnboundLocalError
    vybrany_hrac = None
    
    # 2. Pomocný výpočet pro ikonu míčů
    for zapas in zapasy_v_soutezi:
        if (zapas.id + zapas.hrac_domaci.id + zapas.hrac_hoste.id) % 2 == 0:
            zapas.mice_bere = zapas.hrac_domaci
        else:
            zapas.mice_bere = zapas.hrac_hoste

    # 3. Identifikace hráčů v soutěži
    id_hracu = set()
    for z in zapasy_v_soutezi:
        id_hracu.add(z.hrac_domaci_id)
        id_hracu.add(z.hrac_hoste_id)
    
    hraci_obj = list(Hrac.objects.filter(id__in=id_hracu))
    if not hraci_obj:
        hraci_obj = list(Hrac.objects.filter(klub__iexact=soutez.nazev))

    # 4. Příprava základních seznamů
    vsechny_odehrane = zapasy_v_soutezi.filter(odehrano=True).order_by('-datum', '-id')
    planovane_zapasy = zapasy_v_soutezi.filter(odehrano=False).order_by('datum', 'id')

    # 5. Zpracování filtru (pokud je request)
    if request:
        filtr_hrac_id = request.GET.get('filtr_hrac')
        if filtr_hrac_id and filtr_hrac_id.isdigit():
            vybrany_hrac = Hrac.objects.filter(id=filtr_hrac_id).first()
            if vybrany_hrac:
                vsechny_odehrane = vsechny_odehrane.filter(
                    Q(hrac_domaci=vybrany_hrac) | Q(hrac_hoste=vybrany_hrac)
                )
                planovane_zapasy = planovane_zapasy.filter(
                    Q(hrac_domaci=vybrany_hrac) | Q(hrac_hoste=vybrany_hrac)
                )

    # 6. Výpočet bodů pro tabulku
    for h in hraci_obj:
        h.pocet_bodu, h.s_v, h.s_p = 0, 0, 0
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
                mozne_zapasy = [z for z in zapasy_v_soutezi if 
                               (z.hrac_domaci_id == h_radek.id and z.hrac_hoste_id == h_sloupec.id) or
                               (z.hrac_domaci_id == h_sloupec.id and z.hrac_hoste_id == h_radek.id)]
                
                z_obj = next((z for z in mozne_zapasy if z.odehrano), None)
                if not z_obj and mozne_zapasy:
                    z_obj = mozne_zapasy[0]

                vysledek_v_bunce = None
                if z_obj and z_obj.odehrano:
                    if z_obj.hrac_domaci_id == h_radek.id:
                        vysledek_v_bunce = f"{z_obj.sety_domaci}:{z_obj.sety_hoste}"
                    else:
                        vysledek_v_bunce = f"{z_obj.sety_hoste}:{z_obj.sety_domaci}"

                u = f"{reverse('zadat_vysledek')}?hrac_domaci={h_radek.id}&hrac_hoste={h_sloupec.id}&slug={soutez.slug}"
                
                radek_bunky.append({
                    'typ': 'zapas', 
                    'z': z_obj if (z_obj and z_obj.odehrano) else None, 
                    'vysledek': vysledek_v_bunce,
                    'z_obj': z_obj,
                    'url': u
                })
        matice.append({'hrac': h_radek, 'bunky': radek_bunky})

    # 8. Finální návrat dat
    return {
        'soutez': soutez,
        'hraci': hraci_obj,
        'matice': matice,
        'historie': vsechny_odehrane,
        'planovane': planovane_zapasy,
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
def editovat_vysledek(request, pk):
    zapas = get_object_or_404(Zapas, pk=pk)
    if request.method == 'POST':
        form = ZapasForm(request.POST, instance=zapas)
        if form.is_valid():
            # Tady se děje to kouzlo:
            zapas = form.save(commit=False)
            zapas.odehrano = True  # Automaticky označíme jako odehrané
            zapas.save()           # Teď teprve uložíme do databáze
            return redirect('detail_souteze', soutez_slug=zapas.soutez.slug)
    else:
        form = ZapasForm(instance=zapas)
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
    planovane = vsechny.filter(odehrano=False).order_by('datum')
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
    
