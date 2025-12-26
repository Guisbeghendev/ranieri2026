from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import Group as AuthGroup
from django.utils.translation import gettext_lazy as _

# Importa os modelos necessários
from .models import CustomUser, Profile, Grupo, TipoGrupo, CustomUserTipo, MembroGrupo


@receiver(post_save, sender=CustomUser)
def handle_user_and_group_creation(sender, instance, created, **kwargs):
    """
    1. Cria um objeto Profile para o novo usuário.
    2. Garante que o grupo padrão 'free' e seu metadado Grupo existam.
    3. Associa o novo CustomUser (se não for ADMIN) ao grupo 'free'.
    """
    if created:
        # 1. Cria o Profile (necessário para a integridade)
        Profile.objects.create(user=instance)

    # 2. Garante que o grupo AuthGroup 'free' exista e seu metadado Grupo também.
    FREE_GROUP_NAME = 'free'

    try:
        # Tenta obter o AuthGroup 'free'
        auth_group = AuthGroup.objects.get(name=FREE_GROUP_NAME)

        # Se o AuthGroup existe, mas o metadado Grupo não, cria o metadado
        if not hasattr(auth_group, 'grupo_ranieri'):
            Grupo.objects.create(
                auth_group=auth_group,
                tipo=TipoGrupo.PROJETO,
                descricao=_("Acesso base a conteúdo não segmentado.")
            )
    except AuthGroup.DoesNotExist:
        # Se o AuthGroup não existe, cria o AuthGroup e o metadado Grupo
        auth_group = AuthGroup.objects.create(name=FREE_GROUP_NAME)
        Grupo.objects.create(
            auth_group=auth_group,
            tipo=TipoGrupo.PROJETO,
            descricao=_("Acesso base a conteúdo não segmentado.")
        )

    # 3. Associa o novo CustomUser ao grupo 'free'
    # Esta associação só deve ocorrer na criação e para usuários não-ADMIN
    if created and instance.tipo_usuario != CustomUserTipo.ADMIN:
        try:
            # Reobtém o grupo para garantir que está no contexto correto da transação
            free_auth_group = AuthGroup.objects.get(name=FREE_GROUP_NAME)
            instance.groups.add(free_auth_group)
        except AuthGroup.DoesNotExist:
            # Log de erro, caso o grupo falhe em ser criado, o que é improvável
            # mas garante robustez.
            print(f"ERRO: Grupo '{FREE_GROUP_NAME}' não encontrado para associação do usuário {instance.username}.")


@receiver(post_save, sender=MembroGrupo)
def sincronizar_membro_grupo_save(sender, instance, created, **kwargs):
    """
    Quando um Registro é adicionado a um MembroGrupo,
    adiciona o Usuário vinculado ao grupo de autenticação do Django.
    """
    registro = instance.registro
    if registro and hasattr(registro, 'usuario') and registro.usuario:
        user = registro.usuario
        # Adiciona o usuário ao auth_group do Django vinculado ao Grupo de Audiência
        user.groups.add(instance.grupo.auth_group)


@receiver(post_delete, sender=MembroGrupo)
def sincronizar_membro_grupo_delete(sender, instance, **kwargs):
    """
    Quando um vínculo de MembroGrupo é removido,
    remove o Usuário do grupo de autenticação do Django.
    """
    registro = instance.registro
    if registro and hasattr(registro, 'usuario') and registro.usuario:
        user = registro.usuario
        # Remove o usuário do auth_group do Django
        user.groups.remove(instance.grupo.auth_group)