from django.db import models
from django.utils.translation import gettext_lazy as _

# Importa os modelos CustomUser e Grupo do app 'users'
# O AUTH_USER_MODEL já está configurado para 'users.CustomUser'
from django.conf import settings
from users.models import Grupo


# Modelo que representa o canal de chat, vinculado diretamente a um Grupo de Audiência.
class Canal(models.Model):
    """
    Define um canal de comunicação de tempo real.
    A lista de membros do canal é determinada pelo users.Grupo associado.
    """
    grupo = models.OneToOneField(
        Grupo,
        on_delete=models.CASCADE,
        related_name='canal_chat',
        verbose_name=_("Grupo de Audiência Vinculado"),
        help_text=_("Apenas membros deste Grupo têm acesso ao Canal.")
    )
    nome = models.CharField(
        max_length=100,
        verbose_name=_("Nome Amigável do Canal"),
        # Nome padrão baseado no nome do grupo será populado via signal
    )
    criador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='canais_criados',
        verbose_name=_("Criador do Canal")
    )
    ativo = models.BooleanField(
        default=True,
        verbose_name=_("Canal Ativo")
    )
    criado_em = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        verbose_name = _("Canal de Mensagens")
        verbose_name_plural = _("Canais de Mensagens")

    def save(self, *args, **kwargs):
        # Garante que o nome padrão seja o nome do Grupo, se não for definido
        if not self.pk and not self.nome:
            self.nome = f"Chat: {self.grupo.auth_group.name}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nome} ({self.grupo.auth_group.name})"


# Modelo que armazena o histórico de mensagens
class Mensagem(models.Model):
    """
    Armazena uma única mensagem enviada em um Canal.
    """
    canal = models.ForeignKey(
        Canal,
        on_delete=models.CASCADE,
        related_name='mensagens',
        verbose_name=_("Canal")
    )
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='mensagens_enviadas',
        verbose_name=_("Autor")
    )
    conteudo = models.TextField(
        verbose_name=_("Conteúdo da Mensagem")
    )
    # CORREÇÃO: Renomeado de 'timestamp' para 'data_envio'
    data_envio = models.DateTimeField(
        auto_now_add=True,
        db_index=True, # Importante para consultas eficientes de histórico
        verbose_name=_("Data/Hora de Envio")
    )

    class Meta:
        verbose_name = _("Mensagem")
        verbose_name_plural = _("Mensagens")
        # Ordem padrão para histórico: as mais novas por último (ascendente)
        ordering = ['data_envio']

    def __str__(self):
        return f"[{self.data_envio.strftime('%H:%M')}] {self.autor.username}: {self.conteudo[:50]}..."

    @property
    def autor_nome(self):
        """Retorna o nome amigável do autor."""
        return str(self.autor)