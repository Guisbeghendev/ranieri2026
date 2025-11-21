from django.db import models
from django.utils.translation import gettext_lazy as _


class ProjSimCozinha(models.Model):
    """
    Define cada evento/receita registrada no projeto Simoninha na Cozinha.
    Segue o padrão de Livro Digital para catálogo sequencial de eventos/vídeos.
    """
    titulo = models.CharField(
        max_length=255,
        verbose_name=_('Título do Evento/Receita')
    )

    # Campo para o ID do vídeo (usado no embed)
    link_video = models.CharField(
        max_length=50,
        verbose_name=_('ID do Vídeo (YouTube)'),
        help_text=_('Insira APENAS o ID do vídeo (ex: FjI-N_rA7t0). Usado para incorporação (embed).'),
        unique=True
    )

    # 🚨 NOVO CAMPO: Link completo para acesso externo (botão)
    link_externo = models.URLField(
        verbose_name=_('Link de Acesso Externo'),
        help_text=_('URL completa do vídeo para o botão "Assistir no YouTube" (ex: https://www.youtube.com/watch?v=ID).'),
        unique=True,
        null=True,
        blank=True
    )

    descricao_detalhada = models.TextField(
        verbose_name=_('Descrição Detalhada/Receita'),
        help_text=_('Conteúdo completo do evento ou os passos detalhados da receita.'),
        blank=True
    )

    ordem_exibicao = models.IntegerField(
        verbose_name=_('Ordem de Exibição'),
        help_text=_('Define a sequência cronológica ou temática. Deve ser um número inteiro único.'),
        unique=True
    )

    class Meta:
        verbose_name = _('Evento Simoninha na Cozinha')
        verbose_name_plural = _('Eventos Simoninha na Cozinha')
        # Garante que os eventos sejam sempre listados na ordem correta por padrão
        ordering = ['ordem_exibicao']

    def __str__(self):
        return f'{self.ordem_exibicao} - {self.titulo}'