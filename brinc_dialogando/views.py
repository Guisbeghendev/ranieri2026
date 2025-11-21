from django.shortcuts import render

def index(request):
    """
    Exibe a página de índice do projeto Brincando e Dialogando,
    com informações e link para o canal do YouTube.
    """
    context = {
        'titulo_projeto': 'Brincando e Dialogando',
        'link_canal': 'https://www.youtube.com/c/BrincandoeDialogando'
    }
    return render(request, 'brinc_dialogando/index.html', context)