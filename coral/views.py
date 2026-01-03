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
        except ValueError:
            capitulo_index_atual = 1

        try:
            capitulo = capitulos.get(capitulo_index_base_1=capitulo_index_atual)
        except HistoriaCoral.DoesNotExist:
            capitulo = capitulos.first()
            capitulo_index_atual = 1

        context = {
            'livro_titulo': "História do Coral",
            'capitulo': capitulo,
            'total_capitulos': total_capitulos,
            'capitulo_ordem': capitulo_index_atual,
            'capitulo_anterior': capitulos.filter(capitulo_index_base_1=capitulo_index_atual - 1).first(),
            'proximo_capitulo': capitulos.filter(capitulo_index_base_1=capitulo_index_atual + 1).first(),
        }
        return render(request, self.template_name, context)

class RepertorioListView(View):
    template_name = 'coral/reperto_list.html'

    def get(self, request):
        musicas = RepertorioCoral.objects.all().order_by('-data_criacao')
        return render(request, self.template_name, {'musicas': musicas})