from django.db import models
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.conf import settings


class Hrac(models.Model):
    jmeno = models.CharField(max_length=100, verbose_name="Jméno a příjmení")
    klub = models.CharField(max_length=100, blank=True, null=True, verbose_name="hraje ligu")
    
    # Nové profilové údaje
    foto = models.ImageField(upload_to='hraci/', blank=True, null=True, verbose_name="Fotka")
    datum_narozeni = models.DateField(blank=True, null=True, verbose_name="Datum narození")
    info = models.TextField(blank=True, null=True, verbose_name="O mně / Info")
    adresa = models.CharField(max_length=150, blank=True, verbose_name="adresa")
    
    # Kontaktní údaje
    telefon = models.CharField(max_length=20, blank=True, null=True, verbose_name="Telefon")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    web = models.URLField(blank=True, null=True, verbose_name="Webové stránky")
    
    # Uživatelé s přístupem ke správě hráče / debl páru
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='hrac_profil',
        verbose_name="Uživatel 1"
    )
    druhy_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='hrac_profil_druhy',
        verbose_name="Uživatel 2 (pro debly)"
    )
    
    souteze = models.ManyToManyField(
        'Soutez', 
        blank=True, 
        related_name='hraci', 
        verbose_name="Přihlášen do soutěží"
    )

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

    def ma_pristup(self, check_user):
        """Metoda ověří, zda má přihlášený uživatel (nebo admin) právo spravovat tento profil / zápas."""
        if not check_user or not check_user.is_authenticated:
            return False
        if check_user.is_staff or check_user.is_superuser:
            return True
        return self.user == check_user or self.druhy_user == check_user

    class Meta:
        verbose_name = "Hráč"
        verbose_name_plural = "Hráči"

    def __str__(self):
        return self.jmeno

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
    
    # NOVÉ: Výsledky tiebreaků pro jednotlivé sety (např. '7:3', '5:7' apod.)
    tiebreak_set1 = models.CharField(max_length=10, default='', blank=True, verbose_name="Tiebreak 1. setu")
    tiebreak_set2 = models.CharField(max_length=10, default='', blank=True, verbose_name="Tiebreak 2. setu")
    tiebreak_set3 = models.CharField(max_length=10, default='', blank=True, verbose_name="Tiebreak 3. setu")
    
    # NOVÉ: Textová poznámka k zápasu
    poznamka = models.TextField(blank=True, default='', verbose_name="Poznámka")
    
    sety_domaci = models.IntegerField(default=0)
    sety_hoste = models.IntegerField(default=0)
    gamy_domaci = models.IntegerField(default=0)
    gamy_hoste = models.IntegerField(default=0)
    
    mice_bere_domaci = models.BooleanField(default=True, verbose_name="Míče bere domácí")
    odehrano = models.BooleanField(default=False)
    
    # ÚPRAVA: datum je nyní volitelné (null=True), aby plánované zápasy mohly být prázdné
    datum = models.DateField(null=True, blank=True, verbose_name="Datum zápasu")
    vytvoreno_kdy = models.DateTimeField(auto_now_add=True)
    
    upraveno_kdy = models.DateTimeField(auto_now=True) 

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
    


class SystemLog(models.Model):
    timestamp = models.DateTimeField(default=timezone.now, verbose_name="Čas události")
    source = models.CharField(max_length=255, verbose_name="Zdroj/Funkce")
    user = models.CharField(max_length=100, blank=True, null=True, verbose_name="Uživatel")
    message = models.TextField(verbose_name="Zpráva/Změna")
    is_cron = models.BooleanField(default=False, verbose_name="Automat (Cron)")

    class Meta:
        verbose_name = "Systémový log"
        verbose_name_plural = "Systémové logy"
        ordering = ['-timestamp']

    # Tato metoda nahradí celý složitý logging systém
  
    @staticmethod
    def write(message, user=None, source=None):
            from django.contrib.auth import get_user_model
            
            # Pokud user není objekt uživatele, ale jen None, zkusíme ho označit jako Systém
            display_user = "Systém"
            is_cron = True
            
            if user and not user.is_anonymous:
                display_user = str(user)
                is_cron = False

            SystemLog.objects.create(
                message=message,
                user=display_user,
                source=source or "Unknown",
                is_cron=is_cron
            )

from django.db import models
from django.contrib.auth.models import User

class NastenkaZprava(models.Model):
    nadpis = models.CharField(max_length=200, verbose_name="Nadpis")
    text = models.TextField(verbose_name="Text zprávy")
    autor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Autor")
    datum_vytvoreni = models.DateTimeField(auto_now_add=True, verbose_name="Datum vytvoření")

    class Meta:
        verbose_name = "Zpráva na nástěnce"
        verbose_name_plural = "Zprávy na nástěnce"
        ordering = ['-datum_vytvoreni'] # Nejnovější zprávy první

    def __str__(self):
        return self.nadpis




