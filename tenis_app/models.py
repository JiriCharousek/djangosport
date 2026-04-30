from django.db import models
from django.utils import timezone
from django.utils.safestring import mark_safe




class Hrac(models.Model):
    jmeno = models.CharField(max_length=100, verbose_name="Jméno a příjmení")
    klub = models.CharField(max_length=100, blank=True, null=True, verbose_name="hraje ligu")
    
    # Nové profilové údaje
    foto = models.ImageField(upload_to='hraci/', blank=True, null=True, verbose_name="Fotka")
    datum_narozeni = models.DateField(blank=True, null=True, verbose_name="Datum narození")
    info = models.TextField(blank=True, null=True, verbose_name="O mně / Info")
    
    # Kontaktní údaje
    telefon = models.CharField(max_length=20, blank=True, null=True, verbose_name="Telefon")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    web = models.URLField(blank=True, null=True, verbose_name="Webové stránky")

    @property
    def jmeno_split(self):
            if not self.jmeno:
                return ""
            # Pokud je v názvu " a ", rozdělíme to podle něj
            if " a " in self.jmeno:
                parts = self.jmeno.split(" a ")
                return mark_safe(f"{parts[0]}<br>& {parts[1]}")
            
            # Jinak klasické rozdělení podle první mezery
            parts = self.jmeno.split()
            if len(parts) > 1:
                return mark_safe(f"{parts[0]}<br>{' '.join(parts[1:])}")
            return self.jmeno
  
    class Meta:
        verbose_name = "Hráč"
        verbose_name_plural = "Hráči"
    
    def __str__(self):
        return self.jmeno

    class Meta:
        verbose_name = "Hráč"
        verbose_name_plural = "Hráči"


class Soutez(models.Model):
    slug = models.SlugField(unique=True, max_length=50)
    nazev = models.CharField(max_length=100)
    typ = models.CharField(max_length=2, choices=[('1K', 'Jednokolová'), ('2K', 'Dvoukolová')], default='1K')
    aktivni = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nazev} ({self.slug})"

class Zapas(models.Model):
    VYSLEDKY_SETU = [
        ('0:0', '---'), ('6:0', '6:0'), ('6:1', '6:1'), ('6:2', '6:2'), ('6:3', '6:3'), ('6:4', '6:4'), 
        ('7:5', '7:5'), ('7:6', '7:6'), ('0:6', '0:6'), ('1:6', '1:6'), ('2:6', '2:6'), ('3:6', '3:6'), 
        ('4:6', '4:6'), ('5:7', '5:7'), ('6:7', '6:7'),
    ]

    soutez = models.ForeignKey(Soutez, on_delete=models.CASCADE, related_name='zapasy', null=True)
    hrac_domaci = models.ForeignKey(Hrac, on_delete=models.CASCADE, related_name='domaci')
    hrac_hoste = models.ForeignKey(Hrac, on_delete=models.CASCADE, related_name='hoste')
    set1 = models.CharField(max_length=5, choices=VYSLEDKY_SETU, default='0:0')
    set2 = models.CharField(max_length=5, choices=VYSLEDKY_SETU, default='0:0')
    set3 = models.CharField(max_length=10, default='0:0', blank=True)
    odehrano = models.BooleanField(default=False)
    datum = models.DateField(default=timezone.now)

    def dej_body_ze_setu(self, set_vysledek):
        if not set_vysledek or set_vysledek == '0:0': return 0, 0
        try:
            d, h = map(int, set_vysledek.replace(' ', '').split(':'))
            return d, h
        except: return 0, 0

    @property
    def sety_domaci(self):
        body = 0
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

    def ziskej_body(self):
        if not self.odehrano: return 0, 0
        sd, sh = self.sety_domaci, self.sety_hoste
        if sd > sh: return (3, 0) if sh == 0 else (2, 1)
        return (0, 3) if sd == 0 else (1, 2)

    def __str__(self):
        return f"{self.hrac_domaci} vs {self.hrac_hoste} ({self.sety_domaci}:{self.sety_hoste})"
        
    mice_bere_domaci = models.BooleanField(default=True, verbose_name="Míče bere domácí")
    
    
    