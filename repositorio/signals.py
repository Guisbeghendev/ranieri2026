from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Count, Q
from django.utils import timezone
from .models import Imagem, Galeria


@receiver(post_save, sender=Imagem)
def verificar_status_galeria_apos_processamento(sender, instance, created, **kwargs):
    """
    Este signal é disparado toda vez que um objeto Imagem é salvo (post_save).
    Se o status for 'PROCESSADA', ele verifica a Galeria pai.
    Se todas as imagens da galeria estiverem 'PROCESSADA' (e nenhuma em 'ERRO'),
    o status da Galeria é alterado para 'REVISAO'.
    """
    # 1. Condições de disparo
    # Só agimos se a imagem estiver vinculada a uma galeria
    # E se o campo de processamento foi alterado para PROCESSADA ou ERRO (para re-verificação)
    if not instance.galeria or instance.status_processamento not in ['PROCESSADA', 'ERRO']:
        return

    galeria = instance.galeria

    # 2. Contar as imagens pendentes
    # Consideramos pendentes todas que NÃO estão em PROCESSADA ou ERRO (RASCUNHO, UPLOADED, PROCESSANDO)
    imagens_pendentes_count = Imagem.objects.filter(
        galeria=galeria
    ).exclude(
        status_processamento__in=['PROCESSADA', 'ERRO']
    ).count()

    # 3. Se o count for zero, todas as imagens atingiram um estado final (PROCESSADA ou ERRO).
    if imagens_pendentes_count == 0:

        # Contar quantas imagens estão em ERRO
        imagens_erro_count = Imagem.objects.filter(
            galeria=galeria,
            status_processamento='ERRO'
        ).count()

        # Se houver erros, a galeria precisa de atenção (REVISAO ou, talvez, um novo status de 'ATENCAO')
        if imagens_erro_count > 0:
            novo_status = 'REVISAO'
            print(
                f"Galeria {galeria.nome} alterada para REVISAO (Processamento concluído, mas com {imagens_erro_count} erro(s)).")
        else:
            # Todas as imagens foram PROCESSADAS com sucesso
            novo_status = 'REVISAO'
            print(f"Galeria {galeria.nome} alterada para REVISAO (100% Processamento concluído).")

        # 4. Mudar o status da Galeria, se ela não estiver em um estado final (como PUBLICADA ou ARQUIVADA)
        if galeria.status in ['RASCUNHO', 'PROCESSANDO']:
            galeria.status = novo_status

            # Nota: O campo 'publicada_em' só deve ser preenchido quando o status for alterado para 'PUBLICADA'
            galeria.save(update_fields=['status'])

# Nota: Não é necessário um signal para Curtida.