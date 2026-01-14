import json
from channels.generic.websocket import AsyncWebsocketConsumer

class GaleriaConsumer(AsyncWebsocketConsumer):
    """
    Consumer reativo para progresso de upload e status de galeria.
    """

    async def connect(self):
        # 1. Grupo Global (Lista de Galerias)
        self.global_group = "galerias_status_updates"

        # 2. Grupo Específico
        # Garante a captura segura do PK da URL configurada no routing.py
        self.galeria_id = self.scope.get('url_route', {}).get('kwargs', {}).get('pk')
        self.specific_group = f"galeria_{self.galeria_id}" if self.galeria_id else None

        # Adiciona aos grupos
        await self.channel_layer.group_add(self.global_group, self.channel_name)
        if self.specific_group:
            await self.channel_layer.group_add(self.specific_group, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'global_group'):
            await self.channel_layer.group_discard(self.global_group, self.channel_name)
        if hasattr(self, 'specific_group') and self.specific_group:
            await self.channel_layer.group_discard(self.specific_group, self.channel_name)

    async def status_update(self, event):
        """Atualiza a cor/texto do badge na lista de galerias."""
        await self.send(text_data=json.dumps({
            'type': 'status_galeria',
            'galeria_id': event['galeria_id'],
            'status_display': event['status_display'],
            'status_code': event['status_code']
        }))

    async def notificar_progresso(self, event):
        """Envia progresso individual da imagem e a URL da thumb pronta."""
        await self.send(text_data=json.dumps({
            'type': 'progresso_imagem',
            'imagem_id': event['imagem_id'],
            'progresso': event['progresso'],
            'concluidas': event['concluidas'],
            'total': event['total'],
            'status': event['status'],
            'url_thumb': event['url_thumb']
        }))