from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.urls import reverse
from .models import Hrac, Zapas, Soutez
from .forms import HracForm, ZapasForm

# --- POMOCNÁ FUNKCE PRO VÝPOČET LIGY ---
def vypocitej_ligu(request, pismeno_ligy):
    from django.db.models import Q
    from .models import Hrac, Zapas, Soutez

    # 1. Najdeme objekt ligy (Tento objekt má v sobě to ID, které Django chce)
    liga_obj = Soutez.objects.filter(nazev=pismeno_ligy).first()
    
    # 2. Hráči (zde je to text, takže pismeno_ligy je správně)
    hraci_obj = list(Hrac.objects.filter(klub=pismeno_ligy))
    
    # DEBUG PRO TERMINÁL
    print(f"Hledám hráče s textem v poli klub: {pismeno_ligy}")
    print(f"Počet nalezených hráčů: {len(hraci_obj)}")

    if not liga_obj:
        # Pokud náhodou neexistuje objekt Soutez, ale hráči ano, vytvoříme fake objekt pro šablonu
        class FakeLiga: nazev = pismeno_ligy
        liga_obj = FakeLiga()

    
    # 3. Filtrování historie zápasů
    filtr_hrac_id = request.GET.get('filtr_hrac')
    vybrany_hrac = None
    historie_query = Zapas.objects.filter(odehrano=True, soutez=liga_obj)
    
    if filtr_hrac_id and filtr_hrac_id.isdigit():
        vybrany_hrac = Hrac.objects.filter(id=filtr_hrac_id).first()
        historie = historie_query.filter(Q(hrac_domaci=vybrany_hrac) | Q(hrac_hoste=vybrany_hrac)).order_by('-datum', '-id')
    else:
        historie = historie_query.order_by('-datum', '-id')

# 4. Výpočet statistik
    for h in hraci_obj:
        # --- MUSÍ BÝT TADY NA ZAČÁTKU CYKLU ---
        h.pocet_bodu = 0
        h.s_v = 0  # Sety vyhrané
        h.s_p = 0  # Sety prohrané
        
        # Formátování jména
        casti = h.jmeno.split(' ', 1)
        h.jmeno_split = f"{casti[0]}<br>{casti[1].upper()}" if len(casti) > 1 else h.jmeno.upper()
        
        # Načtení zápasů (používáme liga_obj, protože v Zapasu je to ForeignKey)
        zps = Zapas.objects.filter(
            (Q(hrac_domaci=h) | Q(hrac_hoste=h)), 
            odehrano=True, 
            soutez=liga_obj
        )
        
        for z in zps:
            s_d = z.sety_domaci or 0
            s_h = z.sety_hoste or 0
            
            if z.hrac_domaci == h:
                h.s_v += s_d
                h.s_p += s_h
                if s_d > s_h: h.pocet_bodu += (3 if s_h == 0 else 2)
                else: h.pocet_bodu += (1 if s_d == 1 else 0)
            else:
                h.s_v += s_h
                h.s_p += s_d
                if s_h > s_d: h.pocet_bodu += (3 if s_d == 0 else 2)
                else: h.pocet_bodu += (1 if s_h == 1 else 0)



    # 5. Seřazení tabulky: Body -> Rozdíl setů -> Vyhrané sety
    hraci_obj.sort(key=lambda x: (x.pocet_bodu, (x.s_v - x.s_p), x.s_v), reverse=True)

    # 6. Sestavení křížové matice (Kdo s kým)
    matice = []
    for h_radek in hraci_obj:
        radek_bunky = []
        for h_sloupec in hraci_obj:
            if h_radek == h_sloupec:
                radek_bunky.append({'typ': 'empty'})
            else:
                # Tady opět liga_obj, aby Django nedostalo text 'C' místo čísla ID
                z1 = Zapas.objects.filter(hrac_domaci=h_radek, hrac_hoste=h_sloupec, odehrano=True, soutez=liga_obj).first()
                z2 = Zapas.objects.filter(hrac_domaci=h_sloupec, hrac_hoste=h_radek, odehrano=True, soutez=liga_obj).first()
                
                url_base = reverse('zadat_vysledek')
                u1 = f"?hrac_domaci={h_radek.id}&hrac_hoste={h_sloupec.id}&liga={pismeno_ligy}"
                u2 = f"?hrac_domaci={h_sloupec.id}&hrac_hoste={h_radek.id}&liga={pismeno_ligy}"
                
                radek_bunky.append({
                    'typ': 'zapas', 'z1': z1, 'z2': z2, 'url1': url_base + u1, 'url2': url_base + u2
                })
        matice.append({'hrac': h_radek, 'bunky': radek_bunky})
    
    return {
        'hraci': hraci_obj, 
        'matice': matice, 
        'liga_nazev': pismeno_ligy,
        'historie': historie,
        'vybrany_hrac': vybrany_hrac
    }

# --- POHLEDY PRO JEDNOTLIVÉ LIGY ---
def liga_a(request): return render(request, 'tenis_app/dvoukolova_tabulka.html', vypocitej_ligu(request, "A"))
def liga_b(request): return render(request, 'tenis_app/dvoukolova_tabulka.html', vypocitej_ligu(request, "B"))
def liga_c(request): return render(request, 'tenis_app/dvoukolova_tabulka.html', vypocitej_ligu(request, "C"))
def liga_d(request): return render(request, 'tenis_app/dvoukolova_tabulka.html', vypocitej_ligu(request, "D"))

# --- SPRÁVA HRÁČŮ ---
# def pridat_hrace(request):
    # liga_pismeno = request.GET.get('liga', 'A')
    # if request.method == 'POST':
        # form = HracForm(request.POST)
        # if form.is_valid():
            # hrac = form.save(commit=False)
            # # Přiřazení objektu Soutez
            # liga_obj = Soutez.objects.filter(nazev=request.POST.get('liga_urceni', liga_pismeno)).first()
            # hrac.klub = liga_obj
            # hrac.save()
            # return redirect(f'liga_{liga_pismeno.lower()}')
    # else:
        # form = HracForm()
    # return render(request, 'tenis_app/pridat_hrace.html', {'form': form, 'liga': liga_pismeno})
    
    
def pridat_hrace(request):
    liga_z_url = request.GET.get('liga', 'A') # Získá "C", "B" atd. z URL
    
    if request.method == 'POST':
        form = HracForm(request.POST)
        if form.is_valid():
            hrac = form.save(commit=False)
            
            # POZOR: Pokud hrac.klub je ForeignKey na model Soutez, 
            # musíme najít ten objekt, ne tam vložit jen písmeno.
            liga_obj = Soutez.objects.filter(nazev=liga_z_url).first()
            hrac.klub = liga_obj
            
            hrac.save()
            return redirect(f'liga_{liga_z_url.lower()}')
    else:
        # TATO ČÁST CHYBĚLA - vytvoří prázdný formulář při prvním načtení
        form = HracForm()
    
    # Tento return musí být mimo podmínku POST, aby obsloužil GET i nevalidní formulář
    return render(request, 'tenis_app/pridat_hrace.html', {
        'form': form, 
        'liga': liga_z_url
    })    
    

def editovat_hrace(request, pk):
    hrac = get_object_or_404(Hrac, pk=pk)
    if request.method == 'POST':
        form = HracForm(request.POST, instance=hrac)
        if form.is_valid():
            hrac = form.save()
            # Přesměrování na ligu hráče (pokud existuje)
            return redirect(f'liga_{hrac.klub.nazev.lower()}' if hrac.klub else 'tenis_index')
    else:
        form = HracForm(instance=hrac)
    return render(request, 'tenis_app/editovat_hrace.html', {'form': form, 'hrac': hrac})

    
    
def smazat_hrace(request, pk):
    hrac = get_object_or_404(Hrac, pk=pk)
    # Získáme písmeno ligy z pole klub (pokud tam máš "C", "A" atd.)
    liga_pismeno = (hrac.klub.lower() if hrac.klub else "a")
    
    if request.method == 'POST':
        hrac.delete()
        return redirect(f'liga_{liga_pismeno}')
    
    return render(request, 'tenis_app/potvrdit_smazani.html', {
        'objekt': f"hráče {hrac.jmeno}",
        'zpet_url': f'liga_{liga_pismeno}'  # Toto pošleme do šablony
    })    
    

# --- SPRÁVA VÝSLEDKŮ ---
def zadat_vysledek(request):
    liga_pismeno = request.GET.get('liga', 'A')
    if request.method == 'POST':
        form = ZapasForm(request.POST)
        if form.is_valid():
            zapas = form.save(commit=False)
            # Přiřazení objektu Soutez
            liga_obj = Soutez.objects.filter(nazev=request.POST.get('liga_target', liga_pismeno)).first()
            zapas.soutez = liga_obj
            zapas.save()
            return redirect(f'liga_{liga_pismeno.lower()}')
    else:
        form = ZapasForm(initial={
            'hrac_domaci': request.GET.get('hrac_domaci'), 
            'hrac_hoste': request.GET.get('hrac_hoste')
        })
    return render(request, 'tenis_app/zadat_vysledek.html', {'form': form, 'liga': liga_pismeno})

def editovat_vysledek(request, pk):
    zapas = get_object_or_404(Zapas, pk=pk)
    
    if request.method == 'POST':
        form = ZapasForm(request.POST, instance=zapas)
        if form.is_valid():
            zapas = form.save()  # Tady musíme zavolat .save()!
            # Zjistíme, do které ligy se máme vrátit
            pismeno = zapas.soutez.nazev if zapas.soutez else 'A'
            return redirect(f'/tenis/liga/{pismeno}/') # Vrátí tě to zpět do správné ligy
    else:
        # Když na stránku jen přijdeš (GET), vytvoří se prázdný formulář s daty zápasu
        form = ZapasForm(instance=zapas)
    
    # TENTO ŘÁDEK TI CHYBĚL:
    return render(request, 'tenis_app/editovat_vysledek.html', {
        'form': form,
        'zapas': zapas
    })

def prehled_vsech_zapasu(request):
    vsechny = Zapas.objects.filter(odehrano=True).order_by('-datum', '-id')
    return render(request, 'tenis_app/vsechny_zapasy.html', {
        'historie': vsechny, 
        'titulek': 'Všechny zápasy'
    })
    
    
def smazat_vysledek(request, pk):
    zapas = get_object_or_404(Zapas, pk=pk)
    # Zjistíme pismeno ligy pro návrat (pokud soutez existuje)
    liga_pismeno = zapas.soutez.nazev if zapas.soutez else "A"
    if request.method == 'POST':
        zapas.delete()
        return redirect(f'liga_{liga_pismeno.lower()}')
    return render(request, 'tenis_app/potvrdit_smazani.html', {'objekt': f"zápas {zapas}"})

