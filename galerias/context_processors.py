from repositorio.models import Categoria

def categorias_globais(request):
    return {
        'menu_categorias': Categoria.objects.all().order_by('nome')
    }