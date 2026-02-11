from django.contrib import admin
from .models import Hrac, Zapas, Soutez

# 1. Odregistrujeme vše, co by mohlo dělat neplechu
models_to_clean = [Hrac, Zapas, Soutez]
for m in models_to_clean:
    if admin.site.is_registered(m):
        admin.site.unregister(m)

@admin.register(Soutez)
class SoutezAdmin(admin.ModelAdmin):
    list_display = ('nazev',)  # Necháme jen název, pokud popis neexistuje

# 3. Registrace Hráče
@admin.register(Hrac)
class HracAdmin(admin.ModelAdmin):
    list_display = ('jmeno', 'klub')
    list_filter = ('klub',)
    search_fields = ('jmeno',)

 # 4. Registrace Zápasu
@admin.register(Zapas)
class ZapasAdmin(admin.ModelAdmin):
     list_display = ('datum', 'soutez', 'hrac_domaci', 'hrac_hoste', 'skore_zobrazeni', 'odehrano')
     list_filter = ('soutez', 'odehrano', 'datum')
     search_fields = ('hrac_domaci__jmeno', 'hrac_hoste__jmeno')
     list_editable = ('odehrano',)

     def skore_zobrazeni(self, obj):
         if obj.odehrano:
             return f"{obj.sety_domaci}:{obj.sety_hoste}"
         return "---"
     skore_zobrazeni.short_description = 'Skóre'