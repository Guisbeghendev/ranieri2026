from django.shortcuts import render, get_object_or_404
from django.views import View
from .models import HistoriaCoral, RepertorioCoral
from django.db.models import F
from django.db.models.expressions import Window
from django.db.models.functions import Rank


class CoralIndexView(View):
    template_name = 'coral/coral_index.html'

    def get(self, request):
        return render(request, self.template_name)


class HistoriaDigitalView(View):
    template_name = 'coral/livro_digital_coral.html'

    def get(self, request):
        capitulos = HistoriaCoral.objects.all().order_by('ordem_exibicao').annotate(
            capitulo_index_base_1=Window(
                expression=Rank(),
                order_by=F('ordem_exibicao').asc(),
            )
        )

        total_capitulos = capitulos.count()
        capitulo_ordem = request.GET.get('page', 1)

        try:
            capitulo_index_atual = int(capitulo_ordem)
        except (ValueError, TypeError):
            capitulo_index_atual = 1

        capitulo_lista = list(capitulos)
        try:
            capitulo = capitulo_lista[capitulo_index_atual - 1]
        except (IndexError, ValueError):
            capitulo = capitulo_lista[0] if capitulo_lista else None
            capitulo_index_atual = 1

        context = {
            'livro_titulo': "História do Coral",
            'capitulo': capitulo,
            'total_capitulos': total_capitulos,
            'capitulo_ordem': capitulo_index_atual,
            'capitulo_anterior': capitulo_lista[capitulo_index_atual - 2] if capitulo_index_atual > 1 else None,
            'proximo_capitulo': capitulo_lista[
                capitulo_index_atual] if capitulo_index_atual < total_capitulos else None,
        }
        return render(request, self.template_name, context)


class RepertorioListView(View):
    template_name = 'coral/repertorio_list.html'

    def get(self, request, *args, **kwargs):
        page_num = request.GET.get('page', 1)

        try:
            page_index_base_1 = int(page_num)
        except ValueError:
            page_index_base_1 = 1

        musicas_anotadas = RepertorioCoral.objects.all().annotate(
            musica_index_base_1=Window(
                expression=Rank(),
                order_by=F('ordem_exibicao').asc(),
            )
        ).order_by('ordem_exibicao')

        total_musicas = musicas_anotadas.count()

        if total_musicas == 0:
            context = {
                'total_musicas': 0,
                'livro_titulo': 'Repertório Musical',
            }
            return render(request, self.template_name, context)

        page_index_base_1 = max(1, min(page_index_base_1, total_musicas))

        musicas_lista = list(musicas_anotadas)
        musica_atual = musicas_lista[page_index_base_1 - 1]

        musica_anterior = None
        if page_index_base_1 > 1:
            musica_anterior = musicas_lista[page_index_base_1 - 2]

        proxima_musica = None
        if page_index_base_1 < total_musicas:
            proxima_musica = musicas_lista[page_index_base_1]

        context = {
            'livro_titulo': "Repertório Musical",
            'musica': musica_atual,
            'musica_ordem': page_index_base_1,
            'total_musicas': total_musicas,
            'musica_anterior': musica_anterior,
            'proxima_musica': proxima_musica,
        }

        return render(request, self.template_name, context)