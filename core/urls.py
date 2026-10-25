# core/urls.py
from django.contrib import admin
from django.conf import settings
from django.urls import path, include
from django.views.generic.base import RedirectView
from tenis_app import views as tenis_views

urlpatterns = [
    path('admin/', admin.site.urls),
]

if settings.DEBUG:
    # Lokálně není nastaven SCRIPT_NAME, proto je prefix součástí URL routy.
    urlpatterns += [
        path('', RedirectView.as_view(pattern_name='tenis_app:tenis_index', permanent=False), name='index'),
        path('kaminka/', include('tenis_app.urls', namespace='tenis_app')),
    ]
else:
    # V produkci proxy odstraní /kaminka a FORCE_SCRIPT_NAME ho přidá do
    # URL generovaných Django. Routy proto začínají až za tímto prefixem.
    urlpatterns += [
        path('', tenis_views.tenis_index, name='index'),
        path('', include('tenis_app.urls', namespace='tenis_app')),
    ]

urlpatterns += [
    path('accounts/', include('django.contrib.auth.urls')),
    path('zebricek/', include(('zebricek_app.urls', 'zebricek_app'))),
]

