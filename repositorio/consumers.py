import json
from channels.generic.websocket import AsyncWebsocketConsumer

class GaleriaConsumer(AsyncWebsocketConsumer):
    """
    Consumer para gerenciar atualizações em tempo real na listagem de galerias.
    """
    async def connect(self):
        # Nome do grupo para notificações globais de status de galeria
        self.group_name = "galerias_status_updates"

        # Adiciona o canal ao grupo
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Remove o canal do grupo ao desconectar
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def status_update(self, event):
        """
        Recebe a mensagem do grupo e envia para o WebSocket no navegador.
        """
        galeria_id = event['galeria_id']
        novo_status = event['status_display']
        status_code = event['status_code']

        # Envia os dados para o front-end
        await self.send(text_data=json.dumps({
            'galeria_id': galeria_id,
            'status_display': novo_status,
            'status_code': status_code
        }))