"""
Management-команда: python manage.py seed_data

Создаёт начальные данные для демонстрации работы RBAC:

Ресурсы:   orders, products, reports
Действия:  read, create, update, delete
Роли:
  - admin   → всё на всём
  - manager → read/create/update на orders и products; read на reports
  - viewer  → только read на orders и products

Пользователи:
  - admin@example.com   / admin1234   → роль admin
  - manager@example.com / manager1234 → роль manager
  - viewer@example.com  / viewer1234  → роль viewer
"""

from django.core.management.base import BaseCommand
from access_control.models import Role, Resource, Action, RolePermission, UserRole
from users.models import User

RESOURCES = [
    ('orders', 'Заказы клиентов'),
    ('products', 'Товары каталога'),
    ('reports', 'Отчёты и аналитика'),
]

ACTIONS = [
    ('read', 'Просмотр'),
    ('create', 'Создание'),
    ('update', 'Обновление'),
    ('delete', 'Удаление'),
]

ROLES = [
    ('admin', 'Полный доступ ко всем ресурсам'),
    ('manager', 'Управление заказами и товарами, просмотр отчётов'),
    ('viewer', 'Только просмотр заказов и товаров'),
]

ROLE_PERMISSIONS = {
    'admin': [
        ('orders', 'read'),
        ('orders', 'create'),
        ('orders', 'update'),
        ('orders', 'delete'),
        ('products', 'read'),
        ('products', 'create'),
        ('products', 'update'),
        ('products', 'delete'),
        ('reports', 'read'),
        ('reports', 'create'),
        ('reports', 'update'),
        ('reports', 'delete'),
    ],
    'manager': [
        ('orders', 'read'),
        ('orders', 'create'),
        ('orders', 'update'),
        ('products', 'read'),
        ('products', 'create'),
        ('products', 'update'),
        ('reports', 'read'),
    ],
    'viewer': [
        ('orders', 'read'),
        ('products', 'read'),
    ],
}

USERS = [
    {
        'email': 'admin@example.com',
        'password': 'admin1234',
        'first_name': 'Главный',
        'last_name': 'Администратор',
        'is_staff': True,
        'is_superuser': True,
        'role': 'admin',
    },
    {
        'email': 'manager@example.com',
        'password': 'manager1234',
        'first_name': 'Иван',
        'last_name': 'Менеджеров',
        'patronymic': 'Петрович',
        'is_staff': False,
        'is_superuser': False,
        'role': 'manager',
    },
    {
        'email': 'viewer@example.com',
        'password': 'viewer1234',
        'first_name': 'Мария',
        'last_name': 'Просмотрова',
        'patronymic': 'Ивановна',
        'is_staff': False,
        'is_superuser': False,
        'role': 'viewer',
    },
]


class Command(BaseCommand):
    help = 'Заполняет БД тестовыми данными для демонстрации RBAC'

    def handle(self, *args, **options):
        self.stdout.write('=== Создание ресурсов ===')
        resources = {}
        for name, desc in RESOURCES:
            obj, created = Resource.objects.get_or_create(name=name, defaults={'description': desc})
            resources[name] = obj
            self.stdout.write(f'  {"Создан" if created else "Уже существует"}: {name}')

        self.stdout.write('=== Создание действий ===')
        actions = {}
        for name, desc in ACTIONS:
            obj, created = Action.objects.get_or_create(name=name, defaults={'description': desc})
            actions[name] = obj
            self.stdout.write(f'  {"Создано" if created else "Уже существует"}: {name}')

        self.stdout.write('=== Создание ролей ===')
        roles = {}
        for name, desc in ROLES:
            obj, created = Role.objects.get_or_create(name=name, defaults={'description': desc})
            roles[name] = obj
            self.stdout.write(f'  {"Создана" if created else "Уже существует"}: {name}')

        self.stdout.write('=== Назначение разрешений ролям ===')
        for role_name, perms in ROLE_PERMISSIONS.items():
            role = roles[role_name]
            for resource_name, action_name in perms:
                _, created = RolePermission.objects.get_or_create(
                    role=role,
                    resource=resources[resource_name],
                    action=actions[action_name],
                )
                if created:
                    self.stdout.write(f'  {role_name}: {action_name} → {resource_name}')

        self.stdout.write('=== Создание пользователей ===')
        for user_data in USERS:
            role_name = user_data.pop('role')
            password = user_data.pop('password')

            user, created = User.objects.get_or_create(
                email=user_data['email'],
                defaults={k: v for k, v in user_data.items() if k != 'email'},
            )
            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(self.style.SUCCESS(
                    f'  Создан: {user.email} (пароль: {password})'
                ))
            else:
                self.stdout.write(f'  Уже существует: {user.email}')

            # Назначить роль
            role = roles[role_name]
            _, role_created = UserRole.objects.get_or_create(user=user, role=role)
            if role_created:
                self.stdout.write(f'    Роль назначена: {role_name}')

        self.stdout.write(self.style.SUCCESS('\n✅ Тестовые данные успешно загружены!'))
        self.stdout.write('\nПользователи для входа:')
        self.stdout.write('  admin@example.com   / admin1234   → admin')
        self.stdout.write('  manager@example.com / manager1234 → manager')
        self.stdout.write('  viewer@example.com  / viewer1234  → viewer')
