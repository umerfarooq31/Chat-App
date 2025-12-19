from django.shortcuts import render
from .models import Group, Chat


def index(request, group_name):
    # Get the group or create it if it doesn't exist
    group, created = Group.objects.get_or_create(name=group_name)

    messages = Chat.objects.filter(group=group).order_by('-timestamp')[:50]

    return render(request, 'index.html', {
        'group_name': group_name,
        'chat_messages': reversed(messages)
    })