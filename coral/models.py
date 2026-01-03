import os
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
    nome_exibicao_arquivo = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('Nome de Exibição do Download'),
        help_text=_('Ex: Partitura Soprano. Se vazio, exibe o título da música.')
    )
    video_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name=_('ID do Vídeo (YouTube)'),
        help_text=_('Insira apenas o ID, ex: 9IZYnK4T00Y')
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
        return self.titulo

    @property
    def extensao_arquivo(self):
        if self.arquivo:
            return os.path.splitext(self.arquivo.name)[1].lower()
        return ""