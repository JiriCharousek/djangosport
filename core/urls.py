# core/urls.py
from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # OPRAVA: Místo natvrdo zapsaného '/kaminka/' použijeme jméno URL z tenis_app.
    # Django si cestu sestaví samo a bezpečně bez zdvojování.
    path('', RedirectView.as_view(pattern_name='tenis_app:tenis_index', permanent=False), name='index'),
    
    path('kaminka/', include('tenis_app.urls', namespace='tenis_app')),
    
    path('accounts/', include('django.contrib.auth.urls')),
    path('zebricek/', include(('zebricek_app.urls', 'zebricek_app'))),
]

