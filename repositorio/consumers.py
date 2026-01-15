import json
from channels.generic.websocket import AsyncWebsocketConsumer


class GaleriaConsumer(AsyncWebsocketConsumer):
    """
    Consumer reativo para progresso de upload e status de galeria.
    Utiliza o slug da galeria para identificação do grupo.
    """

    async def connect(self):
        # 1. Grupo Global (Lista de Galerias)
        self.global_group = "galerias_status_updates"

        # 2. Grupo Específico
        # Alterado para capturar o 'slug' da URL, mantendo consistência com tasks.py
        self.galeria_slug = self.scope.get('url_route', {}).get('kwargs', {}).get('slug')

        # Caso não haja slug (ex: upload via dashboard geral), usa o ID do usuário como fallback
        if self.galeria_slug:
            self.specific_group = f"galeria_{self.galeria_slug}"
        else:
            user_id = self.scope.get('user').id if self.scope.get('user') else 'anon'
            self.specific_group = f"galeria_user_{user_id}"

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
            'galeria_id': event.get('galeria_id'),
            'status_display': event.get('status_display'),
            'status_code': event.get('status_code')
        }))

    async def notificar_progresso(self, event):
        """Envia progresso individual da imagem e a URL da thumb pronta."""
        await self.send(text_data=json.dumps({
            'type': 'progresso_imagem',
            'imagem_id': event.get('imagem_id'),
            'progresso': event.get('progresso'),
            'concluidas': event.get('concluidas'),
            'total': event.get('total'),
            'status': event.get('status'),
            'url_thumb': event.get('url_thumb')
        }))