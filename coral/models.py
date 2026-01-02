from django.db import models
from django.utils.translation import gettext_lazy as _

class HistoriaCoral(models.Model):
    titulo = models.CharField(
        max_length=200,
        verbose_name=_('Título do Capítulo')
    )
    conteudo = models.TextField(
        verbose_name=_('Conteúdo (Página)')
    )
    ordem_exibicao = models.IntegerField(
        unique=True,
        verbose_name=_('Ordem de Exibição'),
        help_text=_('Define a sequência lógica (1, 2, 3...)')
    )
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Capítulo de História')
        verbose_name_plural = _('Capítulos de História')
        ordering = ['ordem_exibicao']

    def __str__(self):
        return f"{self.ordem_exibicao}. {self.titulo}"


class RepertorioCoral(models.Model):
    TIPO_ARQUIVO_CHOICES = [
        ('pdf', _('Documento PDF')),
        ('audio', _('Áudio (MP3)')),
        ('video', _('Vídeo (MP4)')),
        ('youtube', _('Link do YouTube')),
    ]

    titulo = models.CharField(
        max_length=200,
        verbose_name=_('Nome da Música')
    )
    arquivo = models.FileField(
        upload_to='coral/repertorio/',
        verbose_name=_('Arquivo de Mídia'),
        blank=True,
        null=True
    )
    video_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name=_('ID do Vídeo (YouTube)'),
        help_text=_('Insira apenas o ID, ex: 9IZYnK4T00Y')
    )
    tipo_arquivo = models.CharField(
        max_length=10,
        choices=TIPO_ARQUIVO_CHOICES,
        verbose_name=_('Tipo do Conteúdo'),
        blank=True,
        null=True
    )
    descricao = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Descrição/Letra')
    )
    data_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Música do Repertório')
        verbose_name_plural = _('Músicas do Repertório')
        ordering = ['-data_criacao']

    def __str__(self):
        return f"[{self.get_tipo_arquivo_display() if self.tipo_arquivo else 'N/A'}] {self.titulo}"