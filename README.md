# Auth & RBAC Backend

Backend-приложение с собственной системой аутентификации и разграничения прав доступа.

**Стек:** Django 5, Django REST Framework, PostgreSQL, JWT (SimpleJWT)

---

## Быстрый старт

```bash
# 1. Зависимости
pip install -r requirements.txt

# 2. Настройка окружения
cp .env.example .env
# заполните .env своими данными

# 3. Миграции
python manage.py migrate

# 4. Тестовые данные (роли, ресурсы, пользователи)
python manage.py seed_data

# 5. Запуск
python manage.py runserver
```

**Тестовые учётные записи после `seed_data`:**

| Email               | Пароль      | Роль    |
|---------------------|-------------|---------|
| admin@example.com   | admin1234   | admin   |
| manager@example.com | manager1234 | manager |
| viewer@example.com  | viewer1234  | viewer  |

---

## Схема базы данных RBAC

### Концепция

Используется модель **RBAC (Role-Based Access Control)** — управление доступом на основе ролей.

```
User ──< UserRole >── Role ──< RolePermission >── Resource
                                      │
                                   Action
```

Пользователь получает доступ к ресурсу **не напрямую**, а через **роль**:

1. Пользователю назначается одна или несколько ролей (`UserRole`)
2. Роль содержит набор разрешений (`RolePermission`)
3. Разрешение — это комбинация: **Действие** (read/create/update/delete) + **Ресурс** (orders/products/reports)

### Таблицы

#### `users_user` — Пользователи

| Поле         | Тип      | Описание                              |
|--------------|----------|---------------------------------------|
| id           | PK       |                                       |
| email        | unique   | Логин (вместо username)               |
| first_name   | varchar  | Имя                                   |
| last_name    | varchar  | Фамилия                               |
| patronymic   | varchar  | Отчество                              |
| password     | varchar  | Хеш пароля (bcrypt)                   |
| is_active    | bool     | False = мягко удалён, вход невозможен |
| is_staff     | bool     | Доступ к Django admin                 |
| is_superuser | bool     | Полный доступ без проверки RBAC       |
| date_joined  | datetime | Дата регистрации                      |

#### `access_control_resource` — Ресурсы

| Поле        | Тип    | Описание                                               |
|-------------|--------|--------------------------------------------------------|
| id          | PK     |                                                        |
| name        | unique | Идентификатор ресурса: `orders`, `products`, `reports` |
| description | text   | Описание                                               |

#### `access_control_action` — Действия

| Поле        | Тип    | Описание                             |
|-------------|--------|--------------------------------------|
| id          | PK     |                                      |
| name        | unique | `read`, `create`, `update`, `delete` |
| description | text   | Описание                             |

#### `access_control_role` — Роли

| Поле        | Тип    | Описание                     |
|-------------|--------|------------------------------|
| id          | PK     |                              |
| name        | unique | `admin`, `manager`, `viewer` |
| description | text   | Описание                     |

#### `access_control_rolepermission` — Разрешения ролей

| Поле        | Тип                      | Описание      |
|-------------|--------------------------|---------------|
| id          | PK                       |               |
| role_id     | FK → Role                |               |
| resource_id | FK → Resource            |               |
| action_id   | FK → Action              |               |
| UNIQUE      | (role, resource, action) | Запрет дублей |

#### `access_control_userrole` — Роли пользователей

| Поле    | Тип          | Описание                  |
|---------|--------------|---------------------------|
| id      | PK           |                           |
| user_id | FK → User    |                           |
| role_id | FK → Role    |                           |
| UNIQUE  | (user, role) | Роль назначается один раз |

### Матрица прав (тестовые данные)

| Роль    | orders:read | orders:create | orders:update | orders:delete | products:read | products:create | products:update | products:delete | reports:read |
|---------|:-----------:|:-------------:|:-------------:|:-------------:|:-------------:|:---------------:|:---------------:|:---------------:|:------------:|
| admin   |      ✅      |       ✅       |       ✅       |       ✅       |       ✅       |        ✅        |        ✅        |        ✅        |      ✅       |
| manager |      ✅      |       ✅       |       ✅       |       ❌       |       ✅       |        ✅        |        ✅        |        ❌        |      ✅       |
| viewer  |      ✅      |       ❌       |       ❌       |       ❌       |       ✅       |        ❌        |        ❌        |        ❌        |      ❌       |

### Алгоритм проверки доступа

```
Запрос к /business/orders/
        │
        ▼
Есть ли JWT-токен в заголовке Authorization?
        │
    НЕТ │                          ДА │
        ▼                             ▼
   401 Unauthorized          Декодировать токен → User
                                      │
                             Пользователь is_active?
                                      │
                                 НЕТ  │          ДА │
                                      ▼              ▼
                              401 Unauthorized   Найти UserRole для User
                                                      │
                                             Найти RolePermission:
                                             role=user_roles,
                                             resource='orders',
                                             action='read'
                                                      │
                                               НАЙДЕНО │   НЕ НАЙДЕНО │
                                                      ▼               ▼
                                             200 + данные      403 Forbidden
```

---

## API Endpoints

### Аутентификация и пользователи

| Метод  | URL                     | Доступ           | Описание                                                                           |
|--------|-------------------------|------------------|------------------------------------------------------------------------------------|
| POST   | `/users/register/`      | Все              | Регистрация (email, first_name, last_name, patronymic, password, password_confirm) |
| POST   | `/users/login/`         | Все              | Вход. Возвращает `access` и `refresh` токены                                       |
| POST   | `/users/token/refresh/` | Все              | Обновление access-токена                                                           |
| POST   | `/users/logout/`        | Авторизован      | Инвалидация refresh-токена (blacklist)                                             |
| GET    | `/users/list/`          | Admin            | Список всех пользователей                                                          |
| GET    | `/users/<id>/detail/`   | Владелец / Admin | Просмотр профиля                                                                   |
| PATCH  | `/users/<id>/update/`   | Владелец / Admin | Обновление профиля / смена пароля                                                  |
| DELETE | `/users/<id>/delete/`   | Владелец / Admin | Мягкое удаление (is_active=False)                                                  |

### Управление правами (только Admin)

| Метод          | URL                                     | Описание                              |
|----------------|-----------------------------------------|---------------------------------------|
| GET/POST       | `/access/resources/`                    | Список / создание ресурсов            |
| GET/PUT/DELETE | `/access/resources/<id>/`               | Управление ресурсом                   |
| GET/POST       | `/access/actions/`                      | Список / создание действий            |
| GET/PUT/DELETE | `/access/actions/<id>/`                 | Управление действием                  |
| GET/POST       | `/access/roles/`                        | Список / создание ролей               |
| GET/PUT/DELETE | `/access/roles/<id>/`                   | Управление ролью                      |
| GET/POST       | `/access/roles/<id>/permissions/`       | Разрешения роли / добавить разрешение |
| DELETE         | `/access/roles/<id>/permissions/<pid>/` | Удалить разрешение у роли             |
| GET/POST       | `/access/user-roles/`                   | Список назначений / назначить роль    |
| DELETE         | `/access/user-roles/<id>/`              | Отозвать роль у пользователя          |
| GET            | `/access/users/<id>/roles/`             | Роли конкретного пользователя         |
| GET            | `/access/my-permissions/`               | Мои права (любой авторизованный)      |

### Бизнес-объекты (Mock)

| Метод  | URL                               | Требуемое право |
|--------|-----------------------------------|-----------------|
| GET    | `/business/orders/`               | orders:read     |
| POST   | `/business/orders/create/`        | orders:create   |
| PUT    | `/business/orders/<id>/update/`   | orders:update   |
| DELETE | `/business/orders/<id>/delete/`   | orders:delete   |
| GET    | `/business/products/`             | products:read   |
| POST   | `/business/products/create/`      | products:create |
| PUT    | `/business/products/<id>/update/` | products:update |
| DELETE | `/business/products/<id>/delete/` | products:delete |
| GET    | `/business/reports/`              | reports:read    |

---

## Ключевые архитектурные решения

### Мягкое удаление

`DELETE /users/<id>/delete/` не удаляет запись из БД. Устанавливает `is_active=False`.  
Django/SimpleJWT при валидации токена проверяет `is_active` — деактивированный пользователь получит 401.

### Logout через blacklist

SimpleJWT поддерживает blacklist refresh-токенов. При logout:

1. Refresh-токен помещается в таблицу `token_blacklist_blacklistedtoken`
2. При следующей попытке использовать этот refresh → ошибка

### Коды ответов

- **401** — нет токена, токен невалиден, пользователь деактивирован
- **403** — токен валиден, но у пользователя нет прав на ресурс

### Хеширование паролей

Пароли никогда не хранятся в открытом виде. Используется `user.set_password()` (PBKDF2-SHA256).
Поле `password` всегда `write_only=True` в сериализаторах.
