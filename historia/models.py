from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


# ==============================================================================
# 🎯 Modelo: HistoricoCapitulo
# Define cada "página" ou marco temporal da narrativa do Livro Digital.
# ==============================================================================

class HistoricoCapitulo(models.Model):
    """
    Representa um único capítulo ou página da história da escola.
    A ordem é definida pelo campo 'ordem_exibicao'.
    """

    titulo = models.CharField(
        max_length=200,
        verbose_name=_("Título do Capítulo")
    )

    # Usamos TextField para conteúdo longo. Se houver necessidade de formatação rica
    # (negrito, links, etc.), este campo pode ser substituído por um HTMLField
    # de uma biblioteca de terceiros (Ex: django-tinymce).
    conteudo = models.TextField(
        verbose_name=_("Conteúdo da Página/Capítulo")
    )

    ordem_exibicao = models.IntegerField(
        unique=True,
        verbose_name=_("Ordem de Exibição"),
        help_text=_("Número único que define a sequência deste capítulo no livro (1, 2, 3, etc.).")
    )

    # --------------------------------------------------------------------------
    # Metadados e Comportamento
    # --------------------------------------------------------------------------

    class Meta:
        verbose_name = _("Capítulo Histórico")
        verbose_name_plural = _("Capítulos Históricos")
        # Garante que a ordem natural de consulta seja a sequência correta
        ordering = ['ordem_exibicao']

    def __str__(self):
        """Representação amigável no Admin."""
        return f"{self.ordem_exibicao}. {self.titulo}"

    # --------------------------------------------------------------------------
    # Validações (Opcional, mas Recomendado)
    # --------------------------------------------------------------------------

    def clean(self):
        """Garante que a ordem de exibição não seja zero ou negativa."""
        super().clean()
        if self.ordem_exibicao is not None and self.ordem_exibicao <= 0:
            raise ValidationError(
                {'ordem_exibicao': _("A ordem de exibição deve ser um número inteiro positivo (maior que zero).")}
            )

    def save(self, *args, **kwargs):
        """Executa a validação 'clean' antes de salvar."""
        self.full_clean()
        super().save(*args, **kwargs)