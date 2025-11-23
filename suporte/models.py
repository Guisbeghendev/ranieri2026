# suporte/models.py

from django.db import models
from django.utils.translation import gettext_lazy as _
# Importe o modelo de usuário customizado do seu app 'users'
# Ajuste 'users.CustomUser' se o seu modelo de usuário estiver em outro local
from users.models import CustomUser
from django.urls import reverse


# ==============================================================================
# 0. CHOICES (Opções de Escolha)
# ==============================================================================

class TopicoStatus(models.TextChoices):
    """
    Define as opções de status para o Tópico de Suporte.
    Essas opções guiam o fluxo de trabalho e as notificações.
    """
    NOVO = 'NOVO', _('Novo')
    EM_ATENDIMENTO = 'ATND', _('Em Atendimento')
    AGUARDANDO_INFO = 'AGRD', _('Aguardando Informação')  # Suporte precisa da resposta do usuário
    RESOLVIDO = 'RESOLV', _('Resolvido')
    FECHADO = 'FECH', _('Fechado/Arquivado')


# ==============================================================================
# 1. MODELO TÓPICO (A Thread Principal)
# ==============================================================================

class Topico(models.Model):
    """
    Representa o tópico (thread) de suporte aberto por um usuário.
    """
    assunto = models.CharField(
        _("Assunto"),
        max_length=255,
        help_text=_("Título conciso da solicitação de suporte.")
    )

    criador = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='topicos_criados',
        verbose_name=_("Criador")
    )

    status = models.CharField(
        _("Status"),
        max_length=6,
        choices=TopicoStatus.choices,
        default=TopicoStatus.NOVO,
        help_text=_("Estado atual do tópico no fluxo de trabalho.")
    )

    admin_responsavel = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='topicos_atendidos',
        verbose_name=_("Admin/Suporte Responsável")
    )

    criado_em = models.DateTimeField(
        _("Criado Em"),
        auto_now_add=True
    )

    # Campo para registrar o último momento de atualização, útil para ordenação
    atualizado_em = models.DateTimeField(
        _("Atualizado Em"),
        auto_now=True
    )

    class Meta:
        verbose_name = _("Tópico de Suporte")
        verbose_name_plural = _("Tópicos de Suporte")
        ordering = ['status', '-atualizado_em']

    def __str__(self):
        return f"Tópico #{self.pk}: {self.assunto} ({self.get_status_display()})"

    def get_absolute_url(self):
        """Retorna a URL canônica para a tela de detalhes do tópico."""
        return reverse('suporte:topico_detail', kwargs={'pk': self.pk})


# ==============================================================================
# 2. MODELO MENSAGEMSUPORTE (Mensagens dentro do Tópico)
# ==============================================================================

class MensagemSuporte(models.Model):
    """
    Representa uma única mensagem postada dentro de um Tópico de Suporte.
    """
    topico = models.ForeignKey(
        Topico,
        on_delete=models.CASCADE,
        related_name='mensagens',
        verbose_name=_("Tópico")
    )

    autor = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='mensagens_suporte_enviadas',
        verbose_name=_("Autor")
    )

    conteudo = models.TextField(
        _("Conteúdo"),
        help_text=_("O texto da comunicação.")
    )

    timestamp = models.DateTimeField(
        _("Data/Hora de Envio"),
        auto_now_add=True
    )

    class Meta:
        verbose_name = _("Mensagem de Suporte")
        verbose_name_plural = _("Mensagens de Suporte")
        ordering = ['timestamp']

    def __str__(self):
        return f"Msg do {self.autor.username} no Tópico #{self.topico.pk} em {self.timestamp.strftime('%Y-%m-%d %H:%M')}"