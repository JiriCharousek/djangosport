from django.shortcuts import render
# Musíš importovat modely ze stejné aplikace
from .models import Clen, PlatbaPrispevku 

def index(request):
    # Přidáme jednoduché ošetření pro případ, že databáze je zatím prázdná
    data = {
        'pocet_clenu': Clen.objects.filter(aktivni=True).count(),
        'neuhrazene_platby': PlatbaPrispevku.objects.filter(zaplaceno=False).count(),
    }
    return render(request, 'fotbal_app/index.html', data)