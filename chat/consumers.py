import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Group, Chat
from django.utils import timezone


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = self.scope['url_route']['kwargs']['group_name']
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def receive(self, text_data):
        data = json.loads(text_data)
        action_type = data.get('type')
        user = self.scope['user']

        # Check if user is logged in
        username = user.username if user.is_authenticated else "Anonymous"

        if action_type == 'typing':
            await self.channel_layer.group_send(
                self.group_name,
                {'type': 'user.typing', 'user': username, 'typing': data['typing']}
            )
        elif action_type == 'delete':
            message_id = data.get('message_id')
            if await self.delete_message_db(user, message_id):
                await self.channel_layer.group_send(
                    self.group_name,
                    {'type': 'chat.delete', 'message_id': message_id}
                )
        else:
            message = data['message']
            time_str = timezone.now().strftime('%I:%M %p').lower()

            # Save to Database
            msg_id = None
            if user.is_authenticated:
                msg_obj = await self.save_message(user, self.group_name, message)
                msg_id = msg_obj.id

            # Broadcast to EVERYONE in the group
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'chat.message',
                    'message': message,
                    'user': username,
                    'time': time_str,
                    'message_id': msg_id
                }
            )

    async def chat_message(self, event):
        # This sends the data back to the browser
        await self.send(text_data=json.dumps({
            'type': 'chat',
            'message': event['message'],
            'user': event['user'],
            'time': event['time'],
            'message_id': event['message_id']
        }))

    async def user_typing(self, event):
        await self.send(text_data=json.dumps({'type': 'typing', 'user': event['user'], 'typing': event['typing']}))

    async def chat_delete(self, event):
        await self.send(text_data=json.dumps({'type': 'delete', 'message_id': event['message_id']}))

    @database_sync_to_async
    def save_message(self, user, group_name, message):
        group, _ = Group.objects.get_or_create(name=group_name)
        return Chat.objects.create(user=user, group=group, content=message)

    @database_sync_to_async
    def delete_message_db(self, user, message_id):
        try:
            msg = Chat.objects.get(id=message_id, user=user)
            msg.delete()
            return True
        except Chat.DoesNotExist:
            return False

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)