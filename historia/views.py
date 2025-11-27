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

        capitulo_atual = None
        proximo_capitulo = None
        capitulo_anterior = None
        total_capitulos = HistoricoCapitulo.objects.count()

        # 2. Busca o Capítulo Atual (Somente se houver capítulos e a ordem for válida)
        if total_capitulos > 0:
            try:
                # Se a ordem solicitada for maior que o total ou menor que 1, tentamos buscar o primeiro.
                if capitulo_ordem > total_capitulos or capitulo_ordem < 1:
                    capitulo_ordem = 1

                # Busca o capítulo pela ordem. Se não existir, a exceção é capturada abaixo.
                capitulo_atual = HistoricoCapitulo.objects.get(ordem_exibicao=capitulo_ordem)

            except HistoricoCapitulo.DoesNotExist:
                # Se o capítulo específico não for encontrado, mas o total > 0,
                # e não conseguimos reverter para a página 1 (o que é improvável se a ordem for bem mantida),
                # levantamos o 404, mas a lógica acima já tenta garantir que isso não ocorra
                # se pelo menos um capítulo existir.
                # No entanto, se total_capitulos for 0, simplesmente 'capitulo_atual' permanece None.
                if capitulo_ordem > 0:
                    # Para tratar o caso em que a ordem solicitada é válida, mas o objeto sumiu
                    raise Http404("Capítulo não encontrado ou sequência inválida.")

        # 3. Busca o Próximo e o Anterior (somente se houver um capítulo atual)
        if capitulo_atual:
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
        # Se 'capitulo_atual' for None, o template deve exibir a mensagem de "sem conteúdo".
        context['capitulo'] = capitulo_atual
        context['capitulo_ordem'] = capitulo_ordem

        # Variáveis de Navegação
        context['proximo_capitulo'] = proximo_capitulo
        context['capitulo_anterior'] = capitulo_anterior

        # Total de capítulos (útil para exibir "Página X de Y")
        context['total_capitulos'] = total_capitulos

        return context