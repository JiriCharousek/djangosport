from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.urls import reverse
from .models import Hrac, Zapas, Soutez
from .forms import HracForm, ZapasForm

# =================================================================
# 1. UNIVERZÁLNÍ VÝPOČETNÍ JÁDRO (Modulární systém)
# =================================================================


def vypocitej_tabulku_dat(soutez, request=None):
    # 1. Nejdříve si připravíme ZÁKLADNÍ QUERYSET všech zápasů této soutěže
    # (Tím vyřešíme tu chybu NameError)
    zapasy_v_soutezi = Zapas.objects.filter(soutez=soutez)
    vsechny_zapasy = zapasy_v_soutezi.filter(odehrano=True)

    # 2. Hledáme unikátní hráče, kteří v této soutěži mají zapsaný zápas
    id_hracu = set()
    for z in zapasy_v_soutezi:
        id_hracu.add(z.hrac_domaci_id)
        id_hracu.add(z.hrac_hoste_id)
    
    # Načteme objekty hráčů (najde to i ty "letní", pokud hrají v této zimní lize)
    hraci_obj = list(Hrac.objects.filter(id__in=id_hracu))
    
    # Fallback pro případ, že soutěž je nová a nemá ještě žádné zápasy
    if not hraci_obj:
        hraci_obj = list(Hrac.objects.filter(klub__iexact=soutez.nazev))

    # 3. Příprava historie pro zobrazení (filtrování podle hráče, pokud je vybrán)
    historie_pro_zobrazeni = vsechny_zapasy.order_by('-datum', '-id')
    vybrany_hrac = None

    if request:
        filtr_hrac_id = request.GET.get('filtr_hrac')
        if filtr_hrac_id and filtr_hrac_id.isdigit():
            vybrany_hrac = Hrac.objects.filter(id=filtr_hrac_id).first()
            if vybrany_hrac:
                historie_pro_zobrazeni = historie_pro_zobrazeni.filter(
                    Q(hrac_domaci=vybrany_hrac) | Q(hrac_hoste=vybrany_hrac)
                )

    # 4. Výpočet bodů do tabulky (počítáme dynamicky v paměti)
    for h in hraci_obj:
        h.pocet_bodu, h.s_v, h.s_p = 0, 0, 0
        zps = vsechny_zapasy.filter(Q(hrac_domaci=h) | Q(hrac_hoste=h))
        for z in zps:
            sd, sh = z.sety_domaci, z.sety_hoste
            if z.hrac_domaci == h:
                h.s_v += sd; h.s_p += sh
                bd, _ = z.ziskej_body()
                h.pocet_bodu += bd
            else:
                h.s_v += sh; h.s_p += sd
                _, bh = z.ziskej_body()
                h.pocet_bodu += bh

    # Seřazení tabulky
    hraci_obj.sort(key=lambda x: (x.pocet_bodu, (x.s_v - x.s_p), x.s_v), reverse=True)

    # 5. Matice (křížová tabulka)
    matice = []
    for h_radek in hraci_obj:
        radek_bunky = []
        for h_sloupec in hraci_obj:
            if h_radek == h_sloupec:
                radek_bunky.append({'typ': 'self' if soutez.typ == '1K' else 'empty'})
            else:
                if soutez.typ == '2K':
                    z1 = vsechny_zapasy.filter(hrac_domaci=h_radek, hrac_hoste=h_sloupec).first()
                    z2 = vsechny_zapasy.filter(hrac_domaci=h_sloupec, hrac_hoste=h_radek).first()
                    u1 = f"{reverse('zadat_vysledek')}?hrac_domaci={h_radek.id}&hrac_hoste={h_sloupec.id}&slug={soutez.slug}"
                    u2 = f"{reverse('zadat_vysledek')}?hrac_domaci={h_sloupec.id}&hrac_hoste={h_radek.id}&slug={soutez.slug}"
                    radek_bunky.append({'typ': 'zapas', 'z1': z1, 'z2': z2, 'url1': u1, 'url2': u2})
                else:
                    z = vsechny_zapasy.filter(
                        (Q(hrac_domaci=h_radek) & Q(hrac_hoste=h_sloupec)) | 
                        (Q(hrac_domaci=h_sloupec) & Q(hrac_hoste=h_radek))
                    ).first()
                    u = f"{reverse('zadat_vysledek')}?hrac_domaci={h_radek.id}&hrac_hoste={h_sloupec.id}&slug={soutez.slug}"
                    radek_bunky.append({'typ': 'zapas', 'z': z, 'url': u})
        matice.append({'hrac': h_radek, 'bunky': radek_bunky})

    return {
        'soutez': soutez,
        'hraci': hraci_obj,
        'hraci_obj': hraci_obj,
        'matice': matice,
        'historie': historie_pro_zobrazeni,
        'vybrany_hrac': vybrany_hrac,
        'pismeno': soutez.nazev
    }
# =================================================================
# 2. HLAVNÍ POHLEDY (Views)
# =================================================================


def detail_souteze(request, soutez_slug):
    soutez = get_object_or_404(Soutez, slug=soutez_slug)
    context = vypocitej_tabulku_dat(soutez, request)
    
    # Přidáme 'tenis_app/' před název souboru
    if soutez.typ == '2K':
        return render(request, 'tenis_app/dvoukolova_tabulka.html', context)
    else:
        return render(request, 'tenis_app/tabulka_5ti_lig.html', context)
    
    

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

def editovat_vysledek(request, pk):
    zapas = get_object_or_404(Zapas, pk=pk)
    if request.method == 'POST':
        form = ZapasForm(request.POST, instance=zapas)
        if form.is_valid():
            form.save()
            return redirect('detail_souteze', soutez_slug=zapas.soutez.slug)
    else:
        form = ZapasForm(instance=zapas)
    return render(request, 'tenis_app/editovat_vysledek.html', {'form': form, 'zapas': zapas})

def smazat_vysledek(request, pk):
    zapas = get_object_or_404(Zapas, pk=pk)
    slug = zapas.soutez.slug
    zapas.delete()
    return redirect('detail_souteze', soutez_slug=slug)

def pridat_hrace(request):
    if request.method == 'POST':
        form = HracForm(request.POST, request.FILES) # Přidejte request.FILES kvůli fotkám
        if form.is_valid():
            form.save()
            return redirect('tenis_index')
    else:
        form = HracForm() # Žádné initial={'klub': ...}
    return render(request, 'tenis_app/pridat_hrace.html', {'form': form})


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


# def editovat_hrace(request, pk):
    # hrac = get_object_or_404(Hrac, pk=pk)
    # if request.method == 'POST':
        # form = HracForm(request.POST, request.FILES, instance=hrac)
        # if form.is_valid():
            # form.save()
            # return redirect('tenis_index')
    # else:
        # form = HracForm(instance=hrac)
    # return render(request, 'tenis_app/editovat_hrace.html', {'form': form})

def smazat_hrace(request, pk):
    hrac = get_object_or_404(Hrac, pk=pk)
    hrac.delete()
    return redirect('tenis_index')

def prehled_vsech_zapasu(request):
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
    

from django.db.models import Q  # Ujisti se, že máš tento import nahoře

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
    
def tenis_index(request):
    souteze = Soutez.objects.filter(aktivni=True)
    return render(request, 'tenis_app/index.html', {'souteze': souteze})
    
