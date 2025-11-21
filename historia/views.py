from django.views.generic import TemplateView
from django.shortcuts import get_object_or_404, render
from django.http import Http404
from .models import HistoricoCapitulo


class LivroDigitalView(TemplateView):
    """
    View que exibe um capítulo específico da história da escola,
    implementando a lógica de navegação sequencial (Livro Digital).
    """
    template_name = 'historia/livro_digital.html'

    def get_context_data(self, **kwargs):
        """
        Calcula o capítulo atual, o anterior e o próximo com base no parâmetro 'page'.
        """
        context = super().get_context_data(**kwargs)

        # 1. Tenta obter o número da página/ordem via URL (GET parameter)
        try:
            # Garante que seja um inteiro e que seja positivo (baseado na validação do modelo)
            capitulo_ordem = int(self.request.GET.get('page', 1))
            if capitulo_ordem <= 0:
                capitulo_ordem = 1
        except ValueError:
            # Se o parâmetro for inválido (não é um número), assume a página 1
            capitulo_ordem = 1

        # 2. Busca o Capítulo Atual
        try:
            # Usa get_object_or_404 para buscar pelo campo 'ordem_exibicao'
            capitulo_atual = HistoricoCapitulo.objects.get(ordem_exibicao=capitulo_ordem)
        except HistoricoCapitulo.DoesNotExist:
            # Se a página solicitada não existir (ex: /historia/?page=999), retorna 404
            raise Http404("Capítulo não encontrado ou sequência inválida.")

        # 3. Busca o Próximo e o Anterior (sem gerar exceção se não existirem)

        # Próximo Capítulo
        ordem_proximo = capitulo_ordem + 1
        proximo_capitulo = HistoricoCapitulo.objects.filter(
            ordem_exibicao=ordem_proximo
        ).first()

        # Capítulo Anterior
        ordem_anterior = capitulo_ordem - 1
        capitulo_anterior = HistoricoCapitulo.objects.filter(
            ordem_exibicao=ordem_anterior
        ).first()

        # 4. Adiciona os dados ao contexto do template
        context['capitulo'] = capitulo_atual
        context['capitulo_ordem'] = capitulo_ordem

        # Variáveis de Navegação
        context['proximo_capitulo'] = proximo_capitulo
        context['capitulo_anterior'] = capitulo_anterior

        # Total de capítulos (útil para exibir "Página X de Y")
        context['total_capitulos'] = HistoricoCapitulo.objects.count()

        return context