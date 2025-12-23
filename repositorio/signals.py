from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Count, Q
from django.utils import timezone
from .models import Imagem, Galeria
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

@receiver(post_save, sender=Imagem)
def verificar_status_galeria_apos_processamento(sender, instance, created, **kwargs):
    """
    Verifica se todas as imagens foram processadas e notifica via WebSocket.
    """
    if not instance.galeria or instance.status_processamento not in ['PROCESSADA', 'ERRO']:
        return

    if kwargs.get('update_fields') and 'status_processamento' not in kwargs.get('update_fields'):
        return

    galeria = instance.galeria

    imagens_pendentes_count = Imagem.objects.filter(
        galeria=galeria
    ).exclude(
        status_processamento__in=['PROCESSADA', 'ERRO']
    ).count()

    if imagens_pendentes_count == 0:
        imagens_erro_count = Imagem.objects.filter(
            galeria=galeria,
            status_processamento='ERRO'
        ).count()

        novo_status = 'RV'

        if galeria.status in ['PR', 'PC']:
            galeria.status = novo_status
            galeria.save(update_fields=['status', 'alterado_em'])

            # NOTIFICAÇÃO VIA WEBSOCKET
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "galerias_status_updates",
                {
                    "type": "status_update",
                    "galeria_id": galeria.id,
                    "status_display": "Pronta para Revisão",
                    "status_code": novo_status,
                }
            )

# Nota: Não é necessário um signal para Curtida.