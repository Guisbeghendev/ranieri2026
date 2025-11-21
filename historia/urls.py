# historia/urls.py

from django.urls import path
from .views import LivroDigitalView # <-- Importação da View

urlpatterns = [
    # Acessível em /historia/ e /historia/?page=X
    path('', LivroDigitalView.as_view(), name='livro_digital'),
]