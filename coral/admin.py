from django.contrib import admin
from .models import HistoriaCoral, RepertorioCoral

@admin.register(HistoriaCoral)
class HistoriaCoralAdmin(admin.ModelAdmin):
    list_display = ('id', 'ordem_exibicao', 'titulo', 'data_atualizacao')
    list_editable = ('ordem_exibicao', 'titulo')
    list_display_links = ('id',)
    search_fields = ('titulo', 'conteudo')
    ordering = ('ordem_exibicao',)

@admin.register(RepertorioCoral)
class RepertorioCoralAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'ordem_exibicao',
        'titulo',
        'video_id',
        'link_externo',
        'extensao_arquivo',
        'data_criacao'
    )
    list_editable = ('ordem_exibicao', 'titulo')
    list_display_links = ('id',)
    search_fields = ('titulo', 'descricao', 'video_id', 'link_externo')
    ordering = ('ordem_exibicao',)
    readonly_fields = ('extensao_arquivo',)

    fieldsets = (
        (None, {
            'fields': ('titulo', 'ordem_exibicao')
        }),
        ('Conteúdo Digital (YouTube)', {
            'fields': ('video_id', 'link_externo'),
            'description': (
                '<div style="background-color: #f0f7ff; border: 1px solid #cce5ff; color: #004085; padding: 10px; border-radius: 5px; margin-top: 10px;">'
                '<strong>Embed:</strong> Use **APENAS O ID** do vídeo (ex: 9IZYnK4T00Y). <br>'
                '<strong>Externo:</strong> Use o **LINK COMPLETO** do YouTube para o botão de segurança.'
                '</div>'
            ),
        }),
        ('Arquivos de Apoio (PDF, MP3, MP4)', {
            'fields': ('arquivo', 'nome_exibicao_arquivo', 'extensao_arquivo'),
            'description': 'Faça o upload e defina o nome que aparecerá no botão de download.'
        }),
        ('Informações Adicionais', {
            'fields': ('descricao',),
        }),
    )

    def save_model(self, request, obj, form, change):
        if obj.video_id:
            import re
            pattern = r'(?:v=|\/)([0-9A-Za-z_-]{11})(?:[%#?&]|$)'
            match = re.search(pattern, obj.video_id)
            if match:
                obj.video_id = match.group(1)
            obj.video_id = obj.video_id.strip()
        super().save_model(request, obj, form, change)