import random
import string
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils.text import slugify
# Předpokládám, že máš model Hrac, pokud ne, uprav na seznam jmen
from tenis_app.models import Hrac 

class Command(BaseCommand):
    help = 'Vygeneruje uživatelské účty pro hráče'

    def handle(self, *args, **options):
        hraci = Hrac.objects.all()
        
        for hrac in hraci:
            # Vytvoření unikátního username
            username = slugify(hrac.jmeno)
            puvodni_username = username
            counter = 1
            
            while User.objects.filter(username=username).exists():
                username = f"{puvodni_username}{counter}"
                counter += 1
            
            # Vygenerování 5místného hesla
            heslo = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
            
            # Vytvoření uživatele (pokud ještě neexistuje vazba)
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(username=username, password=heslo)
                self.stdout.write(f"Hráč: {hrac.jmeno} | User: {username} | Heslo: {heslo}")
                
                # Pokud máš u hráče pole pro Usera, propoj je
                # hrac.user = user
                # hrac.save()