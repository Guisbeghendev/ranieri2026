from django.shortcuts import render

# View da Página Inicial
def home_view(request):
    """
    Função de visualização para a página inicial (Home).
    """
    context = {
        'title': 'Bem-vindo à Escola Estadual Professor José Ranieri'
    }
    return render(request, 'core/home.html', context)