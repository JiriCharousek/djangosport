from django.db import models
from tenis_app.models import Hrac  # Importujeme tvé stávající hráče

class ZebricekPozice(models.Model):
    hrac = models.OneToOneField(Hrac, on_delete=models.CASCADE, related_name='zebricek_data')
    pozice = models.PositiveIntegerField(unique=True)

    class Meta:
        ordering = ['pozice']
        verbose_name = "Pozice v žebříčku"
        verbose_name_plural = "Pozice v žebříčku"

    def __str__(self):
        return f"{self.pozice}. {self.hrac.jmeno}" 
        
