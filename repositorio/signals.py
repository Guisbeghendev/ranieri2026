from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Imagem, Galeria
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

@receiver(post_save, sender=Imagem)
def verificar_status_galeria_apos_processamento(sender, instance, **kwargs):
    """
    Atualiza o status da Galeria para 'RV' (Revisão) apenas quando
    o lote de imagens termina de processar.
    """
    # Só age se a imagem tiver galeria e o status mudou para finalizado
    if not instance.galeria or instance.status_processamento not in ['PROCESSADA', 'ERRO']:
        return

    # Evita recursão infinita verificando se o campo alterado foi o status
    if kwargs.get('update_fields') and 'status_processamento' not in kwargs.get('update_fields'):
        return

    galeria = instance.galeria

    # Verifica se ainda existe alguma imagem sendo carregada ou processada no lote
    tem_pendente = Imagem.objects.filter(
        galeria=galeria,
        status_processamento__in=['UPLOAD_PENDENTE', 'UPLOADED', 'PROCESSANDO']
    ).exists()

    if not tem_pendente:
        # Se a galeria estava em 'Processando' (PC) ou 'Preparando' (PR), move para 'Revisão' (RV)
        if galeria.status in ['PR', 'PC']:
            galeria.status = 'RV'
            galeria.save(update_fields=['status', 'alterado_em'])

            # Notifica o painel administrativo que a galeria mudou de cor/status
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "galerias_status_updates",
                {
                    "type": "status_update",
                    "galeria_id": galeria.id,
                    "status_code": 'RV',
                    "status_display": galeria.get_status_display(),
                }
            )