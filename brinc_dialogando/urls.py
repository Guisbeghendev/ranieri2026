from django.urls import path
from . import views

urlpatterns = [
    # Mapeia a URL raiz do app para a view 'index'
    path('', views.index, name='index'),
]