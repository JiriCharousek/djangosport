from django.db import models
from django.utils import timezone

class Hrac(models.Model):
    jmeno = models.CharField(max_length=100, verbose_name="Jméno")
    klub = models.CharField(max_length=100, blank=True, verbose_name="Liga")
    body = models.IntegerField(default=0)

    def __str__(self):
        return self.jmeno

class Soutez(models.Model):
    NAZEV_CHOICES = [
        ('1K', 'Jednokolová'),
        ('2K', 'Dvoukolová'),
    ]
    nazev = models.CharField(max_length=100) # Např. "Liga A", "Liga B"
    typ = models.CharField(max_length=2, choices=NAZEV_CHOICES, default='2K')
    aktivni = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nazev}"
        
        
class Zapas(models.Model):
    # Definice všech možných výsledků jednoho setu
    VYSLEDKY_SETU = [
        ('0:0', '---'),
        ('6:0', '6:0'), ('6:1', '6:1'), ('6:2', '6:2'), ('6:3', '6:3'), ('6:4', '6:4'), ('7:5', '7:5'), ('7:6', '7:6'),
        ('0:6', '0:6'), ('1:6', '1:6'), ('2:6', '2:6'), ('3:6', '3:6'), ('4:6', '4:6'), ('5:7', '5:7'), ('6:7', '6:7'),
    ]

    soutez = models.ForeignKey(Soutez, on_delete=models.CASCADE, related_name='zapasy', null=True)
    hrac_domaci = models.ForeignKey(Hrac, on_delete=models.CASCADE, related_name='domaci')
    hrac_hoste = models.ForeignKey(Hrac, on_delete=models.CASCADE, related_name='hoste')

    set1 = models.CharField(max_length=5, choices=VYSLEDKY_SETU, default='0:0')
    set2 = models.CharField(max_length=5, choices=VYSLEDKY_SETU, default='0:0')
    set3 = models.CharField(max_length=10, default='0:0', blank=True, help_text="Pro Supertiebreak zadejte skóre ručně (např. 10:8)")
    odehrano = models.BooleanField(default=False)
    datum = models.DateField(default=timezone.now)
    

    # Funkce pro rozbor skóre (např. z "6:4" udělá body)
    def dej_body_ze_setu(self, set_vysledek):
        if not set_vysledek or set_vysledek == '0:0': 
            return 0, 0
        try:
            d, h = map(int, set_vysledek.replace(' ', '').split(':'))
            return d, h
        except:
            return 0, 0

    @property
    def sety_domaci(self):
        body = 0
        # Tady ji voláš jako self.dej_body_ze_setu
        for s in [self.set1, self.set2, self.set3]:
            d, h = self.dej_body_ze_setu(s)
            if d > h: body += 1
        return body

    @property
    def sety_hoste(self):
        body = 0
        for s in [self.set1, self.set2, self.set3]:
            d, h = self.dej_body_ze_setu(s)
            if h > d: body += 1
        return body

    def __str__(self):
        return f"{self.hrac_domaci} vs {self.hrac_hoste} ({self.sety_domaci}:{self.sety_hoste})"
        
    def ziskej_body(self):
        """Vrací (body_domaci, body_hoste) podle tvých pravidel"""
        if not self.odehrano:
            return 0, 0
            
        sd = self.sety_domaci
        sh = self.sety_hoste
        
        if sd > sh:  # Vyhrál domácí
            if sh == 0: return 3, 0  # 2:0
            return 2, 1               # 2:1
        else:        # Vyhrál host
            if sd == 0: return 0, 3  # 0:2
            return 1, 2               # 1:2