from django.contrib import admin
from .models import ZebricekPozice

@admin.register(ZebricekPozice)
class ZebricekPoziceAdmin(admin.ModelAdmin):
    list_display = ('pozice', 'get_hrac_name')
    ordering = ('pozice',)

    def get_hrac_name(self, obj):
        return obj.hrac.jmeno
    get_hrac_name.short_description = 'Hráč'