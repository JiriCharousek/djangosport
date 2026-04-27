# logic.py

def proces_vysledky_ligy(soutez, hraci):
    """Univerzální logika pro výpočet bodů a matice"""
    zapasy = Zapas.objects.filter(soutez=soutez, odehrano=True)
    
    for h in hraci:
        h.pocet_bodu, h.s_v, h.s_p = 0, 0, 0
        # Tady proběhne tvá logika 3-2-1 bodování...
        # ... filtrace zapasy.filter(Q(hrac_domaci=h) | Q(hrac_hoste=h))
        
    hraci = sorted(hraci, key=lambda x: (x.pocet_bodu, (x.s_v - x.s_p)), reverse=True)
    return hraci, zapasy