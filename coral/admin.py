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
    list_display = ('titulo', 'video_id', 'data_criacao')
    search_fields = ('titulo', 'descricao')
    ordering = ('-data_criacao',)

    fieldsets = (
        (None, {
            'fields': ('titulo',)
        }),
        ('Conteúdo Digital (YouTube)', {
            'fields': ('video_id',),
            'description': 'Insira apenas o ID do vídeo (ex: 9IZYnK4T00Y).'
        }),
        ('Arquivos de Apoio (PDF, MP3, MP4)', {
            'fields': ('arquivo',),
            'description': 'Faça o upload aqui para documentos, áudios ou vídeos locais.'
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