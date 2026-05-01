from django.contrib import admin
from .models import Hrac, Zapas, Soutez # Toto je v adminu v pořádku

# 1. Odregistrujeme vše, co by mohlo dělat neplechu
models_to_clean = [Hrac, Zapas, Soutez]
for m in models_to_clean:
    if admin.site.is_registered(m):
        admin.site.unregister(m)

@admin.register(Soutez)
class SoutezAdmin(admin.ModelAdmin):
    list_display = ('nazev', 'slug')  # Necháme jen název, pokud popis neexistuje
    list_filter = ('nazev', 'slug') 
    
# 3. Registrace Hráče
@admin.register(Hrac)
class HracAdmin(admin.ModelAdmin):
    list_display = ('jmeno', 'klub', 'email', 'telefon', 'info')
    list_filter = ('jmeno','klub')
    search_fields = ('jmeno', 'klub')


 # 4. Registrace Zápasu
@admin.register(Zapas)
class ZapasAdmin(admin.ModelAdmin):
    list_display = ('datum', 'soutez', 'hrac_domaci', 'hrac_hoste', 'skore_zobrazeni', 'odehrano')
    list_filter = ('datum', 'soutez', 'hrac_domaci', 'hrac_hoste',  'odehrano')
    search_fields = ('hrac_domaci__jmeno', 'hrac_hoste__jmeno')
    list_editable = ('odehrano',)
    actions = ['hromadne_smazat_datum']
    
    def skore_zobrazeni(self, obj):
         if obj.odehrano:
             return f"{obj.sety_domaci}:{obj.sety_hoste}"
         return "---"
    skore_zobrazeni.short_description = 'Skóre'
    
    @admin.action(description="📅 Smazat datum u vybraných zápasů")
    def hromadne_smazat_datum(self, request, queryset):
        # Hromadná aktualizace v databázi
        pocet = queryset.update(datum=None)
        
      