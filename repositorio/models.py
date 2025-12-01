from django.db import models
from django.conf import settings
from config.storages_conf import PublicMediaStorage, PrivateMediaStorage
from users.models import Grupo
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.utils import timezone

# ==============================================================================
# 1. Configuração da Marca D'água (WatermarkConfig)
# ==============================================================================
class WatermarkConfig(models.Model):
    """
    Define a configuração de uma marca d'água, incluindo o arquivo de imagem
    e a posição onde ela deve ser aplicada.
    """
    POSITIONS = [
        ('TL', 'Top-Left'),
        ('TR', 'Top-Right'),
        ('BL', 'Bottom-Left'),
        ('BR', 'Bottom-Right'),
        ('C', 'Center'),
    ]

    nome = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Nome da Marca D\'água'
    )
    arquivo_marca_dagua = models.ImageField(
        upload_to='watermarks/',
        verbose_name='Arquivo (PNG com Transparência)',
        storage=PublicMediaStorage()
    )
    posicao = models.CharField(
        max_length=2,
        choices=POSITIONS,
        default='BR',
        verbose_name='Posição'
    )
    opacidade = models.FloatField(
        default=0.7,
        help_text='Opacidade de 0.0 (transparente) a 1.0 (sólido).'
    )

    # Rastreamento
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Configuração de Marca D\'água'
        verbose_name_plural = 'Configurações de Marca D\'água'

    def __str__(self):
        return self.nome


# Adiciona um signal para excluir o arquivo do S3 quando o registro for deletado
@receiver(pre_delete, sender=WatermarkConfig)
def delete_watermark_file(sender, instance, **kwargs):
    """
    Deleta o arquivo de marca d'água do S3/Storage antes que o objeto seja
    removido do banco de dados.
    """
    if instance.arquivo_marca_dagua:
        instance.arquivo_marca_dagua.delete(save=False)


# ==============================================================================
# 2. Imagem (Rastreamento de Arquivos)
# ==============================================================================
class Imagem(models.Model):
    """
    Rastreia o arquivo original e o processado (com marca d'água/miniatura)
    no S3 e o seu status de processamento.
    """
    PROCESS_STATUS = [
        ('UPLOAD_PENDENTE', 'Upload Pendente'),
        ('UPLOADED', 'Upload Concluído'),
        ('PROCESSANDO', 'Processando'),
        ('PROCESSADA', 'Processada'),
        ('ERRO', 'Erro no Processamento'),
    ]

    fotografo = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='imagens_enviadas',
        verbose_name='Fotógrafo'
    )

    nome_arquivo_original = models.CharField(
        max_length=255,
        verbose_name='Nome Original do Arquivo'
    )

    arquivo_original = models.FileField(
        upload_to='repo/originais/',
        max_length=500,
        verbose_name='Arquivo Original',
        storage=PrivateMediaStorage()
    )

    arquivo_processado = models.ImageField(
        upload_to='repo/processadas/',
        max_length=500,
        null=True,
        blank=True,
        verbose_name='Arquivo Processado',
        storage=PublicMediaStorage()
    )

    # Ligação com a Galeria (Usa string 'Galeria' para evitar importação circular)
    galeria = models.ForeignKey(
        'Galeria',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='imagens',
        verbose_name='Galeria'
    )

    status_processamento = models.CharField(
        max_length=20,
        choices=PROCESS_STATUS,
        default='UPLOAD_PENDENTE',
        verbose_name='Status do Processamento'
    )

    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Imagem do Repositório'
        verbose_name_plural = 'Imagens do Repositório'

    def __str__(self):
        return self.nome_arquivo_original


# ==============================================================================
# 3. Galeria (Contêiner Principal)
# ==============================================================================
class Galeria(models.Model):
    """
    Contêiner principal para agrupar imagens e definir quem tem acesso.
    """
    STATUS_CHOICES = [
        ('PR', 'Rascunho'),
        ('PC', 'Processando'),
        ('RV', 'Pronta para Revisão'),
        ('PB', 'Publicada'),
        ('AR', 'Arquivada'),
    ]

    nome = models.CharField(max_length=255, verbose_name='Título da Galeria')
    descricao = models.TextField(blank=True, verbose_name='Descrição')

    fotografo = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='galerias_criadas',
        verbose_name='Fotógrafo'
    )

    grupos_acesso = models.ManyToManyField(
        Grupo,
        related_name='galerias_acessiveis',
        verbose_name='Grupos com Acesso'
    )

    # Capa da Galeria (Referência direta, pois Imagem está definida acima)
    capa = models.ForeignKey(
        Imagem,
        on_delete=models.SET_NULL,
        related_name='galeria_capa',
        null=True,
        blank=True,
        verbose_name='Imagem de Capa'
    )

    watermark_config = models.ForeignKey(
        WatermarkConfig,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Marca D\'água Padrão'
    )

    status = models.CharField(
        max_length=2,
        choices=STATUS_CHOICES,
        default='PR',
        verbose_name='Status de Publicação'
    )

    criado_em = models.DateTimeField(auto_now_add=True)
    publicada_em = models.DateTimeField(null=True, blank=True)
    alterado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Galeria'
        verbose_name_plural = 'Galerias'
        ordering = ['-criado_em']

    def __str__(self):
        return f"{self.nome} ({self.status})"

    def publicar(self):
        status_mudou = self.status != 'PB'
        self.status = 'PB'
        if status_mudou:
            self.publicada_em = timezone.now()
            self.save(update_fields=['status', 'publicada_em', 'alterado_em'])
        else:
            self.save(update_fields=['status', 'alterado_em'])
        return status_mudou

    def arquivar(self):
        status_mudou = self.status != 'AR'
        self.status = 'AR'
        self.save(update_fields=['status', 'alterado_em'])
        return status_mudou


# ==============================================================================
# 4. Curtida (Interação do Usuário)
# ==============================================================================
class Curtida(models.Model):
    """
    Rastreia qual usuário (logado) curtiu qual imagem.
    """
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='curtidas',
        verbose_name='Usuário'
    )
    imagem = models.ForeignKey(
        Imagem,
        on_delete=models.CASCADE,
        related_name='curtidas',
        verbose_name='Imagem Curtida'
    )

    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('usuario', 'imagem')
        verbose_name = 'Curtida'
        verbose_name_plural = 'Curtidas'
        ordering = ['-criado_em']

    def __str__(self):
        return f"Curtida por {self.usuario.username} na Imagem {self.imagem.id}"