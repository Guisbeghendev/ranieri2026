from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.exceptions import ObjectDoesNotExist

# Importa o modelo de Grupo do app 'users'
from users.models import Grupo
# Importa o modelo de Canal do app 'mensagens'
from .models import Canal

@receiver(post_save, sender=Grupo)
def criar_ou_atualizar_canal_chat(sender, instance, created, **kwargs):
    """
    Cria ou atualiza automaticamente um Canal de Mensagens quando um Grupo de Audiência é salvo.
    """
    # 1. Tenta obter o CustomUser (criador/admin) para auditoria.
    # Em um cenário real, você buscaria o superusuário padrão ou um admin específico,
    # mas aqui usamos None por simplicidade e segurança (o campo 'criador' é null=True).
    admin_user = None

    if created:
        # Se o Grupo foi recém-criado, cria o Canal de Chat.
        Canal.objects.create(
            grupo=instance,
            nome=f"Chat: {instance.auth_group.name}", # Nome padrão
            criador=admin_user, # Pode ser None ou um usuário admin
            ativo=True
        )
        print(f"SINAL: Canal de Chat criado automaticamente para o Grupo: {instance.auth_group.name}")
    else:
        # Se o Grupo foi atualizado (não criado), atualiza o nome do Canal existente.
        try:
            canal = instance.canal_chat
            # Atualiza o nome do Canal se o nome do Grupo for alterado.
            canal.nome = f"Chat: {instance.auth_group.name}"
            canal.save(update_fields=['nome'])
            print(f"SINAL: Nome do Canal de Chat atualizado para o Grupo: {instance.auth_group.name}")
        except ObjectDoesNotExist:
            # Caso o Canal tenha sido deletado manualmente, mas o Grupo ainda exista,
            # ele será recriado, garantindo a obrigatoriedade.
            Canal.objects.create(
                grupo=instance,
                nome=f"Chat: {instance.auth_group.name}",
                criador=admin_user,
                ativo=True
            )
            print(f"SINAL: Canal de Chat recriado para o Grupo: {instance.auth_group.name}")

@receiver(post_delete, sender=Grupo)
def deletar_canal_chat(sender, instance, **kwargs):
    """
    Deleta o Canal de Mensagens associado quando o Grupo de Audiência é deletado.
    Como Canal usa models.OneToOneField(..., on_delete=models.CASCADE) para o Grupo,
    este signal é tecnicamente redundante para a exclusão do Canal, mas serve
    como um excelente log de auditoria e garante a remoção explícita.
    """
    try:
        # Tenta acessar o Canal via related_name, se ainda existir
        canal = instance.canal_chat
        canal.delete()
        print(f"SINAL: Canal de Chat associado ao Grupo {instance.auth_group.name} deletado.")
    except ObjectDoesNotExist:
        # Se o Canal já foi deletado (via CASCADE), apenas registra.
        print(f"SINAL: Canal de Chat não encontrado para exclusão (já deletado via CASCADE para o Grupo {instance.auth_group.name}).")
    except Exception as e:
        print(f"SINAL ERRO: Falha ao tentar deletar Canal associado ao Grupo {instance.auth_group.name}: {e}")