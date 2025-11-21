from django.contrib import admin
from .models import HistoricoCapitulo


# ==============================================================================
# 🎯 Admin para HistoricoCapitulo
# Garante a ordenação e a edição rápida da ordem de exibição.
# ==============================================================================

@admin.register(HistoricoCapitulo)
class HistoricoCapituloAdmin(admin.ModelAdmin):
    """
    Configuração do Admin para o modelo HistoricoCapitulo.
    Foca na facilidade de visualização e reordenação.
    """

    # Campos a serem exibidos na lista (list_display)
    list_display = (
        'ordem_exibicao',
        'titulo',
    )

    # Permite editar a ordem de exibição diretamente na lista.
    # Isso é crucial para um Livro Digital onde a sequência importa.
    list_editable = (
        'ordem_exibicao',
    )

    # Define a ordenação padrão da lista
    # (importante para que list_editable funcione bem)
    ordering = (
        'ordem_exibicao',
    )

    # Campos que se tornam links para a página de edição
    list_display_links = (
        'titulo',
    )

    # Campos a serem pesquisados
    search_fields = (
        'titulo',
        'conteudo'
    )

    # Organiza os campos na página de edição
    fieldsets = (
        (None, {
            'fields': ('titulo', 'conteudo'),
            'description': 'Informações do conteúdo do capítulo.',
        }),
        ('Controle de Sequência', {
            'fields': ('ordem_exibicao',),
            'description': 'Número único que define a posição do capítulo no livro.',
        }),
    )