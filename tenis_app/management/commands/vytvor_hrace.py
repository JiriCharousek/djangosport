import random
import string
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils.text import slugify
from tenis_app.models import Hrac

class Command(BaseCommand):
    def handle(self, *args, **options):
        hraci = Hrac.objects.all()
        
        for hrac in hraci:
            if not hrac.jmeno:
                self.stdout.write(self.style.ERROR(f"Hráč ID {hrac.id} nemá jméno!"))
                continue

            username = slugify(hrac.jmeno)
            # Vygenerujeme nové 5místné heslo
            heslo = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
            
            # Najde uživatele nebo ho vytvoří
            user, created = User.objects.get_or_create(username=username)
            
            # VŽDY nastavíme nové heslo (reset)
            user.set_password(heslo)
            user.save()
            
            # VŽDY zapíšeme do pole info
            hrac.info = f"Login: {username} | Heslo: {heslo}"
            hrac.save()
            
            self.stdout.write(self.style.SUCCESS(f"OK: {hrac.jmeno} -> {username} ({heslo})"))