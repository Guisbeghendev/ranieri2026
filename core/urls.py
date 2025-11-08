from django.urls import path
from . import views

# Define o namespace do App para evitar conflitos de nome
app_name = 'core'

urlpatterns = [
    # Mapeia a URL raiz ('/') para a view da página inicial
    path('', views.home_view, name='home'),
]