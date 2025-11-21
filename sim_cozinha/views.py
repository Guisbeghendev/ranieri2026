from django.shortcuts import render, get_object_or_404
from django.views import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.db.models import F
from django.db.models.expressions import Window
from django.db.models.functions import Rank
from .models import ProjSimCozinha

# Define a quantidade máxima de itens por página (sempre 1 para o Livro Digital)
ITENS_POR_PAGINA = 1


# 🚨 NOVA VIEW PARA A PÁGINA INICIAL DO MÓDULO
class IndexSimCozinhaView(View):
    """
    View para a página inicial do módulo Simoninha na Cozinha.
    """
    template_name = 'sim_cozinha/index_sim_cozinha.html'

    def get(self, request, *args, **kwargs):
        context = {
            'titulo_projeto': 'Projeto Simoninha na Cozinha',
            'link_canal': 'https://www.youtube.com/@SeuCanalDoYoutube', # 🚨 SUBSTITUA PELO SEU LINK DO CANAL
        }
        return render(request, self.template_name, context)


@method_decorator(login_required, name='dispatch')
class ProjSimCozinhaView(View):
    """
    View para exibir o Catálogo de Eventos/Receitas 'Simoninha na Cozinha'
    no formato de Livro Digital sequencial. Requer login obrigatório.
    """
    template_name = 'sim_cozinha/catalogo_sim_cozinha.html'

    def get(self, request, *args, **kwargs):
        # 1. Determina a página/capítulo atual
        # O parâmetro 'page' na URL representa a ordem_exibicao do capítulo
        page_num = request.GET.get('page', 1)

        try:
            # O índice base 1 do capítulo atual
            page_index_base_1 = int(page_num)
        except ValueError:
            # Se o valor for inválido, volta para o primeiro capítulo
            page_index_base_1 = 1

        # 2. Consulta de Capítulos com Rank (necessário para navegação sequencial)
        # Calcula a posição (rank) de cada objeto ProjSimCozinha baseado na ordem_exibicao
        capitulos_anotados = ProjSimCozinha.objects.filter(link_video__isnull=False).annotate( # 🚨 Filtrado para ter video
            # Adiciona uma coluna 'capitulo_index_base_1' (rank) ao queryset
            capitulo_index_base_1=Window(
                expression=Rank(),
                order_by=F('ordem_exibicao').asc(),
            )
        ).order_by('ordem_exibicao') # 🚨 Adicionado order_by explícito para consistência

        # 3. Determina o Capítulo Atual e o Total
        total_capitulos = capitulos_anotados.count()

        if total_capitulos == 0:
            # Não há conteúdo cadastrado
            context = {
                'total_capitulos': 0,
                'catalogo_titulo': 'Simoninha na Cozinha - Catálogo de Eventos',
            }
            return render(request, self.template_name, context)

        # Garante que o índice não exceda o total ou seja menor que 1
        page_index_base_1 = max(1, min(page_index_base_1, total_capitulos))

        # Obtém o objeto do catálogo (capítulo) que corresponde ao índice
        capitulo_atual = get_object_or_404(
            capitulos_anotados,
            capitulo_index_base_1=page_index_base_1
        )

        # 4. Determina os Capítulos de Navegação (Anterior e Próximo)
        capitulo_anterior = None
        if page_index_base_1 > 1:
            capitulo_anterior = capitulos_anotados.filter(
                capitulo_index_base_1=(page_index_base_1 - 1)
            ).first()

        proximo_capitulo = None
        if page_index_base_1 < total_capitulos:
            proximo_capitulo = capitulos_anotados.filter(
                capitulo_index_base_1=(page_index_base_1 + 1)
            ).first()

        # 5. Contexto para o Template
        context = {
            # Títulos
            'catalogo_titulo': 'Simoninha na Cozinha - Catálogo de Eventos',
            'titulo_pagina': capitulo_atual.titulo,

            # Navegação
            'capitulo': capitulo_atual,
            'capitulo_ordem': page_index_base_1,
            'total_capitulos': total_capitulos,
            'capitulo_anterior': capitulo_anterior,
            'proximo_capitulo': proximo_capitulo,
        }

        return render(request, self.template_name, context)