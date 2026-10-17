from django.db import models
from django.utils import timezone

class Clen(models.Model):
    KATEGORIE_CHOICES = [
        ('U9', 'Mladší přípravka'),
        ('U11', 'Starší přípravka'),
        ('U13', 'Mladší žáci'),
        ('U15', 'Starší žáci'),
        ('MUZ', 'Muži'),
    ]

    jmeno = models.CharField(max_length=100)
    prijmeni = models.CharField(max_length=100)
    datum_narozeni = models.DateField()
    email_rodice = models.EmailField(blank=True, null=True)
    telefon = models.CharField(max_length=15, blank=True)
    kategorie = models.CharField(max_length=3, choices=KATEGORIE_CHOICES)
    variabilni_symbol = models.PositiveIntegerField(unique=True, help_text="ID pro párování plateb")
    aktivni = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.prijmeni} {self.jmeno} ({self.kategorie})"

    class Meta:
        verbose_name = "Člen"
        verbose_name_plural = "Členové"

class PlatbaPrispevku(models.Model):
    clen = models.ForeignKey(Clen, on_delete=models.CASCADE, related_name='platby')
    sezona = models.CharField(max_length=20, help_text="Např. Podzim 2026")
    castka = models.DecimalField(max_digits=8, decimal_places=2)
    datum_splatnosti = models.DateField()
    zaplaceno = models.BooleanField(default=False)
    datum_uhrady = models.DateField(null=True, blank=True)

    def __str__(self):
        status = "Zaplaceno" if self.zaplaceno else "Dluží"
        return f"{self.clen.prijmeni} - {self.sezona} ({status})"

    class Meta:
        verbose_name = "Platba"
        verbose_name_plural = "Platby"
        
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

