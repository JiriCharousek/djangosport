# core/urls.py
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView
# Ujisti se, že importuješ views, pokud ho používáš, ale pro index.html ho nepotřebuješ


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='index.html'), name='index'),
    
    path('kaminka/', include(('tenis_app.urls', 'tenis_app'))),
    
    path('accounts/', include('django.contrib.auth.urls')),
    path('zebricek/', include(('zebricek_app.urls', 'zebricek_app'))),
]