from django.contrib import admin
from .models import Clen, PlatbaPrispevku

@admin.register(Clen)
class ClenAdmin(admin.ModelAdmin):
    list_display = ('prijmeni', 'jmeno', 'kategorie', 'variabilni_symbol', 'aktivni')
    list_filter = ('kategorie', 'aktivni')
    search_fields = ('prijmeni', 'jmeno', 'variabilni_symbol')

@admin.register(PlatbaPrispevku)
class PlatbaAdmin(admin.ModelAdmin):
    list_display = ('clen', 'sezona', 'castka', 'datum_splatnosti', 'zaplaceno')
    list_filter = ('zaplaceno', 'sezona')
    list_editable = ('zaplaceno',) # Umožňuje rychle "odklikat" platby přímo v seznamu
    search_fields = ('clen__prijmeni', 'clen__variabilni_symbol')