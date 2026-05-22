from django.core.management.base import BaseCommand
from users.models import User


class Command(BaseCommand):
    help = 'Создаёт суперпользователя admin@example.com / admin1234'

    def handle(self, *args, **options):
        email = 'admin@example.com'
        password = 'admin1234'

        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.WARNING(f'Пользователь {email} уже существует.'))
            return

        user = User.objects.create(
            email=email,
            first_name='Главный',
            last_name='Администратор',
            is_active=True,
            is_staff=True,
            is_superuser=True,
        )
        user.set_password(password)
        user.save()

        self.stdout.write(self.style.SUCCESS(
            f'Суперпользователь создан: {email} / {password}'
        ))
