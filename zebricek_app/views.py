from django.shortcuts import render, get_object_or_404
from .models import ZebricekPozice
import logging
logger = logging.getLogger(__name__)
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import ZebricekPozice
from tenis_app.models import Hrac # Ujisti se, že importuješ model Hrac
from django.shortcuts import render, get_object_or_404, redirect  # Přidáno 'redirect'
from django.http import HttpResponse
from .models import ZebricekPozice
from django.db import transaction
import math
from .models import ZebricekPozice

@login_required
def zebricek_index(request):
    vsechny_pozice = ZebricekPozice.objects.all().select_related('hrac').order_by('pozice')
    moje_data = vsechny_pozice.filter(hrac__user=request.user).first()
    
    # Automatický výpočet poloviny
    pocet_hracu = vsechny_pozice.count()
    polovina = math.ceil(pocet_hracu / 2)

    # Rozdělení na dva seznamy (sloupce)
    sloupec_1 = vsechny_pozice[:polovina]
    sloupec_2 = vsechny_pozice[polovina:]
    
    # Zde si ponechte logiku pro mozni_souperi_ids, kterou už v kódu máte
    mozni_souperi_ids = []
    if moje_data:
        mozni_souperi = vsechny_pozice.filter(
            pozice__in=[moje_data.pozice - 1, moje_data.pozice - 2, moje_data.pozice - 3],
            pozice__gt=0
        )
        mozni_souperi_ids = [p.hrac.id for p in mozni_souperi]

    return render(request, 'zebricek_app/zebricek_list.html', {
        'sloupec_1': sloupec_1,
        'sloupec_2': sloupec_2,
        'zebricek': vsechny_pozice, # Ponecháno pro admin panel a celkový přehled
        'moje_data': moje_data,
        'mozni_souperi_ids': mozni_souperi_ids,
    })

def aktualizuj_pozice_zebricku(zapas):
    print(f"--- DEBUG ŽEBŘÍČEK: Start pro zápas ID {zapas.id} ---")
    
    # 1. Kontrola soutěže (vypneme přísnost, pokud slug nesedí přesně)
    if not zapas.soutez:
        print("DEBUG: Zápas nemá přiřazenou soutěž, končím.")
        return
    
    print(f"DEBUG: Soutěž zápasu je: {zapas.soutez.slug}")

    # 2. Získání dat obou hráčů
    try:
        p_domaci = zapas.hrac_domaci.zebricek_data
        p_hoste = zapas.hrac_hoste.zebricek_data
        print(f"DEBUG: Pozice v DB - Domácí({zapas.hrac_domaci.jmeno}): {p_domaci.pozice}, Hosté({zapas.hrac_hoste.jmeno}): {p_hoste.pozice}")
    except Exception as e:
        print(f"DEBUG: Chyba - jeden z hráčů není v žebříčku: {e}")
        return

    # 3. Kdo je vyzyvatel? (Ten s vyšším číslem pozice = horší místo)
    if p_domaci.pozice > p_hoste.pozice:
        vyzyvatel_data, obhajce_data = p_domaci, p_hoste
    else:
        vyzyvatel_data, obhajce_data = p_hoste, p_domaci

    # 4. Kdo vyhrál podle setů?
    print(f"DEBUG: Skóre setů: {zapas.sety_domaci}:{zapas.sety_hoste}")
    
    vitez = None
    if zapas.sety_domaci > zapas.sety_hoste:
        vitez = zapas.hrac_domaci
    elif zapas.sety_hoste > zapas.sety_domaci:
        vitez = zapas.hrac_hoste

    if not vitez:
        print("DEBUG: Remíza nebo nezadané sety, neprohazuji.")
        return

    # 5. Pokud vyhrál vyzyvatel, prohodíme je
    if vitez == vyzyvatel_data.hrac:
        print(f"🔥 VÝMĚNA: {vitez.jmeno} porazil obhájce!")
        
        stara_pozice_obhajce = obhajce_data.pozice
        stara_pozice_vyzyvatele = vyzyvatel_data.pozice
        
        # TRIK: Dočasně odsuneme vyzyvatele na "neexistující" pozici (třeba 0 nebo hodně vysoké číslo)
        # Tím uvolníme jeho pozici (např. 10), aby na ni mohl skočit obhájce
        vyzyvatel_data.pozice = 99999 
        vyzyvatel_data.save()
        
        # Teď můžeme obhájci dát pozici 10, protože 99999 nikoho nepálí
        obhajce_data.pozice = stara_pozice_vyzyvatele
        obhajce_data.save()
        
        # A nakonec vyzyvateli dáme tu lepší pozici (např. 8)
        vyzyvatel_data.pozice = stara_pozice_obhajce
        vyzyvatel_data.save()
        
        print(f"✅ POZICE PROHOZENY: {vitez.jmeno} je nyní na pozici {stara_pozice_obhajce}")
    else:
        print(f"DEBUG: Vyhrál obhájce {vitez.jmeno}, pozice zůstávají.")
        

from django.db import transaction

@login_required
def manualni_posun_hrace(request):
    if not request.user.is_staff: # Jen pro adminy
        return HttpResponse("Nemáš oprávnění.")

    if request.method == 'POST':
        hrac_id = request.POST.get('hrac_id')
        nova_pozice = int(request.POST.get('nova_pozice'))
        
        with transaction.atomic():
            # 1. Najdeme data hráče, kterého chceme posunout
            target_data = get_object_or_404(ZebricekPozice, hrac_id=hrac_id)
            stara_pozice = target_data.pozice
            
            if stara_pozice == nova_pozice:
                return redirect('zebricek_app:zebricek_index')

            # 2. Uvolníme místo (odsuneme ostatní)
            if nova_pozice < stara_pozice:
                # Posouváme se nahoru: lidi mezi novou a starou pozicí jdou o 1 dolů
                posunuti = ZebricekPozice.objects.filter(
                    pozice__gte=nova_pozice, 
                    pozice__lt=stara_pozice
                ).order_by('-pozice') # Důležité: brát odzadu kvůli UNIQUE chybě
            else:
                # Posouváme se dolů: lidi mezi starou a novou pozicí jdou o 1 nahoru
                posunuti = ZebricekPozice.objects.filter(
                    pozice__gt=stara_pozice, 
                    pozice__lte=nova_pozice
                ).order_by('pozice')

            # Provedeme odsun pomocí triku s 99999, aby to neházelo UNIQUE chybu
            target_data.pozice = 99999
            target_data.save()

            for p in posunuti:
                if nova_pozice < stara_pozice:
                    p.pozice += 1
                else:
                    p.pozice -= 1
                p.save()

            # 3. Dosadíme hráče na finální místo
            target_data.pozice = nova_pozice
            target_data.save()

    return redirect('zebricek_app:zebricek_index')




