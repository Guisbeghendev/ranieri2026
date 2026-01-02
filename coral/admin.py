from django.contrib import admin
from .models import HistoriaCoral, RepertorioCoral

@admin.register(HistoriaCoral)
class HistoriaCoralAdmin(admin.ModelAdmin):
    list_display = ('ordem_exibicao', 'titulo', 'data_atualizacao')
    list_editable = ('titulo',)
    search_fields = ('titulo', 'conteudo')
    ordering = ('ordem_exibicao',)

@admin.register(RepertorioCoral)
class RepertorioCoralAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'tipo_arquivo', 'data_criacao')
    list_filter = ('tipo_arquivo',)
    search_fields = ('titulo', 'descricao')
    ordering = ('-data_criacao',)

    fieldsets = (
        (None, {
            'fields': ('titulo', 'tipo_arquivo')
        }),
        ('Conteúdo Digital (YouTube)', {
            'fields': ('video_url',),
            'description': 'Preencha este campo se o tipo for "Link do YouTube".'
        }),
        ('Arquivos de Apoio (PDF, MP3, MP4)', {
            'fields': ('arquivo',),
            'description': 'Faça o upload aqui para documentos, áudios ou vídeos locais.'
        }),
        ('Informações Adicionais', {
            'fields': ('descricao',),
        }),
    )