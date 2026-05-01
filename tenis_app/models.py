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
    
    sety_domaci = models.IntegerField(default=0)
    sety_hoste = models.IntegerField(default=0)
    gamy_domaci = models.IntegerField(default=0)
    gamy_hoste = models.IntegerField(default=0)
    
    mice_bere_domaci = models.BooleanField(default=True, verbose_name="Míče bere domácí")
    odehrano = models.BooleanField(default=False)
    
    # ÚPRAVA: datum je nyní volitelné (null=True), aby plánované zápasy mohly být prázdné
    datum = models.DateField(null=True, blank=True, verbose_name="Datum zápasu")

    class Meta:
        unique_together = ('soutez', 'hrac_domaci', 'hrac_hoste')
        ordering = ['-datum', 'hrac_domaci']


    def dej_body_ze_setu(self, set_vysledek):
        if not set_vysledek or set_vysledek == '0:0': return 0, 0
        try:
            # Ošetření případných mezer a rozdělení
            d, h = map(int, set_vysledek.replace(' ', '').split(':'))
            return d, h
        except: return 0, 0

    def save(self, *args, **kwargs):
        # 1. AUTOMATICKÉ PŘIŘAZENÍ MÍČŮ (Vaše stávající logika)
        if self.mice_bere_domaci is None:
            soucet = (self.hrac_domaci.id or 0) + (self.hrac_hoste.id or 0)
            self.mice_bere_domaci = (soucet % 2 == 0)

        # 2. VÝPOČET SKÓRE (Vaše stávající logika)
        sd, sh = 0, 0
        gd, gh = 0, 0
        for s in [self.set1, self.set2, self.set3]:
            d, h = self.dej_body_ze_setu(s)
            gd += d
            gh += h
            if d > h: sd += 1
            elif h > d: sh += 1
        
        self.sety_domaci = sd
        self.sety_hoste = sh
        self.gamy_domaci = gd
        self.gamy_hoste = gh

        # --- NOVÁ ČÁST: 2.5 AUTOMATICKÉ PŘEPNUTÍ ODEHRÁNO ---
        # Pokud součet setů dává smysluplný výsledek (např. někdo vyhrál aspoň jeden set),
        # automaticky zápas označíme za odehraný.
        if sd > 0 or sh > 0:
            self.odehrano = True
            
        else:
            self.odehrano = False # Toto zajistí, že při smazání setů zápas "vypadne" z tabulky
        # ----------------------------------------------------
        
        # 3. ULOŽENÍ DO DATABÁZE
        super().save(*args, **kwargs)


    def ziskej_body(self):
        if not self.odehrano: return 0, 0
        sd, sh = self.sety_domaci, self.sety_hoste
        if sd > sh: return (3, 0) if sh == 0 else (2, 1)
        return (0, 3) if sd == 0 else (1, 2)

    def __str__(self):
        return f"{self.hrac_domaci} vs {self.hrac_hoste} ({self.sety_domaci}:{self.sety_hoste})"
    