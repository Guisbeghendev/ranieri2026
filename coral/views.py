from django.shortcuts import get_object_or_404, render
from django.views import View
from .models import CapituloCoral
from django.db.models import F
from django.db.models.expressions import Window # CORREÇÃO: Importar Window de expressions
from django.db.models.functions import Rank # CORREÇÃO: Importar Rank de functions
from django.http import Http404

# Mapeamento para determinar o tipo de livro
LIVRO_MAP = {
    'historia': CapituloCoral.LIVRO_HISTORIA,
    'repertorio': CapituloCoral.LIVRO_REPERTORIO,
}

class CoralIndexView(View):
    """
    View que exibe a página inicial do Coral com as opções de livros (História e Repertório).
    """
    template_name = 'coral/coral_index.html'

    def get(self, request):
        context = {
            'livro_historia_url': CapituloCoral.LIVRO_HISTORIA,
            'livro_repertorio_url': CapituloCoral.LIVRO_REPERTORIO,
        }
        return render(request, self.template_name, context)


class LivroDigitalCoralView(View):
    template_name = 'coral/livro_digital_coral.html'

    def get(self, request, tipo_livro_url):
        # 1. Determina o tipo de livro
        tipo_livro = LIVRO_MAP.get(tipo_livro_url)
        if not tipo_livro:
            raise Http404("Livro não encontrado.")

        # 2. Filtra todos os capítulos e calcula o rank/ordem de exibição no DB
        capitulos = CapituloCoral.objects.filter(tipo_livro=tipo_livro).order_by('ordem_exibicao').annotate(
            # Otimização: calcula a posição indexada (1-based) no próprio banco de dados
            capitulo_index_base_1=Window(
                expression=Rank(),
                order_by=F('ordem_exibicao').asc(),
            )
        )

        if not capitulos.exists():
             return render(request, self.template_name, {
                'livro_titulo': CapituloCoral.TIPO_LIVRO_CHOICES[0][1] if tipo_livro == CapituloCoral.LIVRO_HISTORIA else CapituloCoral.TIPO_LIVRO_CHOICES[1][1],
                'capitulo': None,
                'total_capitulos': 0,
                'capitulo_ordem': 0,
                'url_rota': tipo_livro_url # Mantém a url_rota mesmo sem capítulos
            })

        total_capitulos = capitulos.count()
        primeiro_capitulo_index = capitulos.first().capitulo_index_base_1 # Posição 1

        # 3. Obtém o número da página atual (index 1-based)
        capitulo_ordem = request.GET.get('page')

        try:
            # Se 'page' for fornecido, usa-o. Caso contrário, usa a primeira ordem.
            capitulo_index_atual = int(capitulo_ordem) if capitulo_ordem else primeiro_capitulo_index
            if capitulo_index_atual < 1 or capitulo_index_atual > total_capitulos:
                 capitulo_index_atual = primeiro_capitulo_index # Garante que seja um valor válido

        except ValueError:
            capitulo_index_atual = primeiro_capitulo_index

        # 4. Obtém o capítulo atual usando a posição calculada no banco de dados (capitulo_index_base_1)
        try:
            # A posição é 1-based, então usamos index=N. No SQL, ele busca o N-ésimo resultado após a ordenação.
            capitulo = capitulos.get(capitulo_index_base_1=capitulo_index_atual)
        except CapituloCoral.DoesNotExist:
             # Fallback para o primeiro capítulo se algo falhar
            capitulo = capitulos.first()
            capitulo_index_atual = primeiro_capitulo_index

        # 5. Prepara a lógica de navegação (anterior e próximo)

        # Capítulo anterior (posição - 1)
        capitulo_anterior_obj = capitulos.filter(capitulo_index_base_1=capitulo_index_atual - 1).first()

        # Próximo capítulo (posição + 1)
        proximo_capitulo_obj = capitulos.filter(capitulo_index_base_1=capitulo_index_atual + 1).first()


        context = {
            # Título do livro dinâmico para o template
            'livro_titulo': capitulo.get_tipo_livro_display(),
            'capitulo': capitulo,
            'total_capitulos': total_capitulos,
            'capitulo_ordem': capitulo_index_atual, # Usamos o index 1-based para o display e cálculo de progresso
            'capitulo_anterior': capitulo_anterior_obj,
            'proximo_capitulo': proximo_capitulo_obj,
            'url_rota': tipo_livro_url, # O slug ('historia' ou 'repertorio')
            'tipo_livro_constante': tipo_livro # Usado para os links de troca de livro no template
        }

        return render(request, self.template_name, context)