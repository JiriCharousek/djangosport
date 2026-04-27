from django.urls import path
from . import views

app_name = 'fotbal'

urlpatterns = [
    path('', views.index, name='index'),
    # Sem pak budeme přidávat cesty pro evidenci členů a plateb
]


