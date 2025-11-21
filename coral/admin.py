from django.contrib import admin
from .models import CapituloCoral


@admin.register(CapituloCoral)
class CapituloCoralAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'tipo_livro', 'ordem_exibicao', 'data_atualizacao')
    list_filter = ('tipo_livro',)
    search_fields = ('titulo', 'conteudo')
    # Permite editar a ordem diretamente na lista, mas o ideal é no formulário
    list_editable = ('ordem_exibicao',)

    fieldsets = (
        (None, {
            'fields': ('tipo_livro', 'titulo', 'conteudo'),
        }),
        ('Controle de Navegação', {
            'fields': ('ordem_exibicao',),
            'description': 'A ordem de exibição deve ser única para cada Tipo de Livro.'
        }),
    )

    # Ordena por tipo de livro e ordem de exibição no admin
    ordering = ('tipo_livro', 'ordem_exibicao')