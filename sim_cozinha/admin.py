from django.contrib import admin
from .models import ProjSimCozinha


@admin.register(ProjSimCozinha)
class ProjSimCozinhaAdmin(admin.ModelAdmin):
    # Campos exibidos na lista (index) do Admin
    list_display = (
        'ordem_exibicao',
        'titulo',
        'link_video_exibir',  # Campo de método para exibir o link
        'link_externo',  # 🚨 NOVO CAMPO: Link externo
        'id',
    )

    # Campos que podem ser usados para buscar
    search_fields = (
        'titulo',
        'descricao_detalhada',
        'link_video',
        'link_externo', # 🚨 NOVO CAMPO
    )

    # Campos que podem ser usados para filtrar a lista
    list_filter = (
        'ordem_exibicao',
    )

    # Campos somente leitura (o ID é útil, mas não deve ser editado)
    readonly_fields = (
        'id',
    )

    # Ordem de exibição padrão (por ordem_exibicao)
    ordering = (
        'ordem_exibicao',
    )

    # Campos exibidos no formulário de edição/criação
    fieldsets = (
        (None, {
            'fields': (
                'titulo',
                'ordem_exibicao',
                'id'
            ),
        }),
        ('Conteúdo e Mídia', {
            'fields': (
                'link_video',
                'link_externo', # 🚨 NOVO CAMPO
                'descricao_detalhada',
            ),
            # Lembrete ajustado para os dois campos
            'description': (
                '<div style="background-color: #f0f7ff; border: 1px solid #cce5ff; color: #004085; padding: 10px; border-radius: 5px; margin-top: 10px;">'
                '<strong>Embed:</strong> Use **APENAS O ID** do vídeo (campo "ID do Vídeo"). <br>'
                '<strong>Externo:</strong> Use o **LINK COMPLETO** do YouTube (campo "Link de Acesso Externo").'
                '</div>'
            ),
        }),
    )

    # Método para exibir o link de vídeo de forma simplificada na listagem
    def link_video_exibir(self, obj):
        # Exibe o ID do vídeo (que agora é o link_video)
        return obj.link_video

    link_video_exibir.short_description = 'ID do Vídeo'