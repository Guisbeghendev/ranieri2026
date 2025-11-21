from django.db import models
from django.utils.translation import gettext_lazy as _

class CapituloCoral(models.Model):

    # Opções de Tipo de Livro para segmentação
    LIVRO_HISTORIA = 'historia'
    LIVRO_REPERTORIO = 'repertorio'

    TIPO_LIVRO_CHOICES = [
        (LIVRO_HISTORIA, _('História do Coral')),
        (LIVRO_REPERTORIO, _('Repertório')),
    ]

    # Campos do modelo
    tipo_livro = models.CharField(
        max_length=20,
        choices=TIPO_LIVRO_CHOICES,
        default=LIVRO_HISTORIA,
        verbose_name=_('Tipo de Livro')
    )
    titulo = models.CharField(
        max_length=200,
        verbose_name=_('Título do Capítulo')
    )
    conteudo = models.TextField(
        verbose_name=_('Conteúdo (Página)')
    )
    # ordem_exibicao deve ser único dentro do escopo de tipo_livro
    ordem_exibicao = models.IntegerField(
        verbose_name=_('Ordem de Exibição'),
        help_text=_('Define a sequência lógica de visualização (1, 2, 3...). Deve ser único por Tipo de Livro.')
    )
    data_criacao = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Data de Criação')
    )
    data_atualizacao = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Última Atualização')
    )

    class Meta:
        verbose_name = _('Capítulo do Coral')
        verbose_name_plural = _('Capítulos do Coral')
        # Garante que a ordem_exibicao seja única APENAS dentro do mesmo tipo_livro
        unique_together = ('tipo_livro', 'ordem_exibicao')
        ordering = ['tipo_livro', 'ordem_exibicao']

    def __str__(self):
        return f"[{self.get_tipo_livro_display()}] {self.ordem_exibicao}. {self.titulo}"