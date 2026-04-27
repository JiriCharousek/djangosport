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