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
    # 🚨 ADIÇÃO: Campo slug para URLs amigáveis
    slug = models.SlugField(
        unique=True,
        max_length=100,
        verbose_name=_("Slug do Canal"),
        help_text=_("Identificador único para URLs.")
    )


    class Meta:
        verbose_name = _("Canal de Mensagens")
        verbose_name_plural = _("Canais de Mensagens")

    def save(self, *args, **kwargs):
        from django.utils.text import slugify

        # Garante que o nome padrão seja o nome do Grupo, se não for definido
        if not self.pk and not self.nome:
            self.nome = f"Chat: {self.grupo.auth_group.name}"

        # 🚨 ADIÇÃO: Garante que o slug seja preenchido (essencial para URLs)
        if not self.slug:
             self.slug = slugify(self.nome)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nome} ({self.grupo.auth_group.name})"

    # 🚨 ADIÇÃO: Propriedade para retornar usuários (Baseado no Grupo)
    @property
    def users(self):
        """Retorna a QuerySet de todos os usuários que são membros do Grupo vinculado."""
        # Assume que o modelo Grupo tem uma relação com os usuários
        return settings.AUTH_USER_MODEL.objects.filter(groups__in=[self.grupo.auth_group])


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


# ==============================================================================
# 🚨 NOVO MODELO DE RASTREAMENTO DE LEITURA
# ==============================================================================
class UltimaLeituraUsuario(models.Model):
    """
    Rastreia o momento em que um usuário leu pela última vez um Canal específico.
    Usado para determinar se há mensagens novas (não lidas).
    """
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ultimas_leituras',
        verbose_name=_("Usuário")
    )
    canal = models.ForeignKey(
        Canal,
        on_delete=models.CASCADE,
        related_name='leituras_usuarios',
        verbose_name=_("Canal")
    )
    # data_leitura deve ser atualizada manualmente na view quando o usuário acessar o chat
    data_leitura = models.DateTimeField(
        auto_now=True, # Atualiza automaticamente na hora do save()
        verbose_name=_("Data da Última Leitura")
    )

    class Meta:
        verbose_name = _("Última Leitura do Usuário")
        verbose_name_plural = _("Últimas Leituras dos Usuários")
        # Garante que um usuário só tenha um registro de leitura por canal
        unique_together = ('usuario', 'canal')

    def __str__(self):
        return f"Última leitura de {self.usuario.username} em {self.canal.nome}"