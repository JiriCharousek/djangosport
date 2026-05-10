from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView # Toto potřebujeme pro index.html
from django.views.generic.base import RedirectView


urlpatterns = [
    path('admin/', admin.site.urls),
    
    # 1. Přesměrování úplného základu (sportadmin.cz) do nového adresáře
    path('', RedirectView.as_view(url='/kaminka/tenis/liga/26_kaminka_leto_D/'), name='home'),

    # 2. Všechny tenisové věci teď budou pod /kaminka/tenis/...
    path('kaminka/', include([
    path('tenis/', include('tenis_app.urls')),
        # Pokud máš další aplikace, dej je sem do seznamu
    path('accounts/', include('django.contrib.auth.urls')),
    
    path('zebricek/', include('zebricek_app.urls')),
    ])),
]