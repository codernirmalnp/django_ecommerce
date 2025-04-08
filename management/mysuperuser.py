import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Account

class Command(BaseCommand):
    def handle(self, *args, **options):
        if not Account.objects.filter(username='myuser').exists():
            Account.objects.create_superuser('myuser',
                                          'myuser@myemail.com',
                                          'mypassword')