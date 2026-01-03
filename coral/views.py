from django.shortcuts import render
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

    def get(self, request):
        musicas_qs = RepertorioCoral.objects.all().order_by('data_criacao').annotate(
            musica_index_base_1=Window(
                expression=Rank(),
                order_by=F('data_criacao').asc(),
            )
        )

        total_musicas = musicas_qs.count()
        musica_ordem = request.GET.get('page', 1)

        try:
            musica_index_atual = int(musica_ordem)
        except (ValueError, TypeError):
            musica_index_atual = 1

        musicas_lista = list(musicas_qs)

        try:
            musica = musicas_lista[musica_index_atual - 1]
        except (IndexError, ValueError):
            musica = musicas_lista[0] if musicas_lista else None
            musica_index_atual = 1

        context = {
            'livro_titulo': "Repertório Musical",
            'musica': musica,
            'total_musicas': total_musicas,
            'musica_ordem': musica_index_atual,
            'musica_anterior': musicas_lista[musica_index_atual - 2] if musica_index_atual > 1 else None,
            'proxima_musica': musicas_lista[musica_index_atual] if musica_index_atual < total_musicas else None,
        }
        return render(request, self.template_name, context)