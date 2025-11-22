import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from datetime import datetime

# Importa os modelos necessários
from .models import Canal, Mensagem
# Importa Grupo para validação de membros.
from users.models import Grupo

# Obtém o modelo CustomUser (users.CustomUser)
CustomUser = get_user_model()


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """
    Gerencia conexões WebSocket para um canal de chat específico.
    Realiza a validação de membro do grupo e o salvamento de mensagens.
    **ADICIONADO**: Eventos de entrada e saída de membros.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.canal_id = None
        self.canal_group_name = None
        self.user = None
        self.canal_obj = None

    # ======================================================================
    # Métodos Auxiliares Assíncronos (Database Access)
    # ======================================================================

    @database_sync_to_async
    def get_user_display_name(self, user):
        """ Retorna o nome completo ou username do usuário. """
        return user.get_full_name() or user.username

    @database_sync_to_async
    def get_canal_and_validate_user(self, canal_id, user):
        """
        Busca o Canal e verifica se o CustomUser logado é membro do Grupo associado.
        Retorna o objeto Canal se o usuário for válido.
        """
        try:
            # 1. Busca o Canal
            canal = Canal.objects.select_related('grupo', 'grupo__auth_group').get(id=canal_id)
        except Canal.DoesNotExist:
            return None, "Canal não encontrado."

        # 2. Validação de Autenticação
        if not user.is_authenticated:
            return None, "Usuário não autenticado."

        # 3. Validação de Membro do Grupo (usando o ManyToManyField reverso customizado)
        # Verifica se o CustomUser está no Group do Django associado ao Grupo do Canal.
        is_member = canal.grupo.auth_group.customuser_set.filter(id=user.id).exists()

        if not is_member:
            return None, "Usuário não é membro deste Canal."

        return canal, None

    @database_sync_to_async
    def save_message(self, canal, user, content):
        """
        Salva a mensagem no banco de dados e retorna o conteúdo formatado.
        """
        # Salva a mensagem no modelo Mensagem
        mensagem = Mensagem.objects.create(
            canal=canal,
            autor=user,
            conteudo=content
        )

        # Retorna o dicionário de dados para ser enviado ao grupo do Channels
        return {
            'autor_nome': mensagem.autor.get_full_name() or mensagem.autor.username,
            'conteudo': mensagem.conteudo,
            # Garante que seja string para serialização JSON
            'timestamp': mensagem.data_envio.strftime('%H:%M'),
            'user_id': str(user.id),
        }

    # ======================================================================
    # Métodos de Conexão WebSocket
    # ======================================================================

    async def connect(self):
        """
        Chamado quando o WebSocket tenta se conectar.
        Valida a permissão e aceita/rejeita a conexão.
        """
        self.canal_id = self.scope['url_route']['kwargs']['canal_id']
        self.canal_group_name = f'chat_{self.canal_id}'
        self.user = self.scope["user"]

        # Valida a permissão do usuário no banco de dados
        self.canal_obj, error_message = await self.get_canal_and_validate_user(self.canal_id, self.user)

        if self.canal_obj is None:
            # Rejeita a conexão se a validação falhar
            print(
                f"WS CONNECTION REJECTED for user {self.user.username if self.user.is_authenticated else 'Anonymous'}: {error_message}")
            await self.close()
        else:
            # 1. Se for membro válido, aceita a conexão e entra no grupo do Channels
            await self.channel_layer.group_add(
                self.canal_group_name,
                self.channel_name
            )
            await self.accept()
            print(f"WS CONNECTION ACCEPTED for user {self.user.username} on canal {self.canal_id}")

            # 2. **NOVO:** Envia o evento de 'user_join' para o grupo
            user_display_name = await self.get_user_display_name(self.user)

            await self.channel_layer.group_send(
                self.canal_group_name,
                {
                    'type': 'user.status',  # Novo handler
                    'action': 'join',
                    'user_id': str(self.user.id),
                    'username': self.user.username,
                    'display_name': user_display_name,
                    'initials': self.user.username[0].upper(),
                }
            )

    async def disconnect(self, close_code):
        """
        Chamado quando o WebSocket se desconecta.
        Remove o usuário do grupo e envia evento de saída.
        """
        if self.canal_group_name and self.user and self.user.is_authenticated:
            # 1. Envia o evento de 'user_leave' para o grupo
            user_display_name = await self.get_user_display_name(self.user)

            await self.channel_layer.group_send(
                self.canal_group_name,
                {
                    'type': 'user.status',  # Novo handler
                    'action': 'leave',
                    'user_id': str(self.user.id),
                    'username': self.user.username,
                    'display_name': user_display_name,
                }
            )

            # 2. Remove o usuário do grupo
            await self.channel_layer.group_discard(
                self.canal_group_name,
                self.channel_name
            )
            print(f"WS DISCONNECTED for user {self.user.username}")

    async def receive_json(self, content, **kwargs):
        """
        Chamado quando uma mensagem JSON é recebida do WebSocket (do cliente).
        Salva a mensagem e a retransmite para todos os membros do grupo.
        """
        message_type = content.get("type", "message")
        message_content = content.get("message", "").strip()

        if message_type == "message" and message_content and self.canal_obj:
            # 1. Salva a mensagem no banco de dados
            message_data = await self.save_message(
                self.canal_obj, self.user, message_content
            )

            # 2. Envia a mensagem para o grupo de canais
            await self.channel_layer.group_send(
                self.canal_group_name,
                {
                    'type': 'chat.message',
                    'text': message_data,
                }
            )
        elif not self.canal_obj:
            print("ERROR: Mensagem recebida sem canal_obj configurado.")

    # ======================================================================
    # Métodos de Tratamento de Eventos (Handlers)
    # ======================================================================

    async def chat_message(self, event):
        """
        Chamado quando uma mensagem é recebida do grupo (de outro usuário/processo).
        Envia a mensagem (JSON) de volta ao cliente.
        """
        message_to_send = event["text"]
        message_to_send['type'] = 'chat_message'
        await self.send_json(message_to_send)

    async def user_status(self, event):
        """
        **NOVO**
        Chamado quando um evento user_join ou user_leave é recebido do grupo.
        Envia o status do usuário (JSON) de volta ao cliente.
        """
        # Garante que apenas o tipo e os dados relevantes sejam enviados
        payload = {
            'type': f'user_{event["action"]}',  # Será 'user_join' ou 'user_leave'
            'user_id': event['user_id'],
            'username': event['username'],
            'display_name': event['display_name'],
            # Inclui iniciais apenas no join (para renderização)
            'initials': event.get('initials'),
        }
        await self.send_json(payload)