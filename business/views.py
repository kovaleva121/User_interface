"""
Mock-вьюхи бизнес-объектов.
Таблицы в БД не создаются — данные возвращаются статически.
Доступ проверяется через RBAC: роль → действие → ресурс.
Если пользователь не залогинен → 401.
Если залогинен, но нет прав → 403.
"""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from access_control.permissions import (
    CanReadOrders, CanCreateOrders, CanUpdateOrders, CanDeleteOrders,
    CanReadProducts, CanCreateProducts, CanUpdateProducts, CanDeleteProducts,
    CanReadReports,
)

# ─── Заглушки данных ────────────────────────────────────────────────────────

MOCK_ORDERS = [
    {'id': 1, 'client': 'ООО Ромашка', 'product': 'Ноутбук Dell', 'qty': 3, 'status': 'pending', 'total': 285000},
    {'id': 2, 'client': 'ИП Смирнов', 'product': 'Монитор LG 27"', 'qty': 10, 'status': 'shipped', 'total': 340000},
    {'id': 3, 'client': 'АО Техносфера', 'product': 'Клавиатура Logitech', 'qty': 50, 'status': 'delivered',
     'total': 175000},
    {'id': 4, 'client': 'ООО Глобал', 'product': 'SSD Samsung 1TB', 'qty': 20, 'status': 'cancelled', 'total': 160000},
]

MOCK_PRODUCTS = [
    {'id': 1, 'name': 'Ноутбук Dell XPS 15', 'category': 'Ноутбуки', 'price': 95000, 'stock': 12},
    {'id': 2, 'name': 'Монитор LG 27UK850', 'category': 'Мониторы', 'price': 34000, 'stock': 30},
    {'id': 3, 'name': 'Клавиатура Logitech MX', 'category': 'Периферия', 'price': 3500, 'stock': 100},
    {'id': 4, 'name': 'SSD Samsung 970 EVO 1TB', 'category': 'Накопители', 'price': 8000, 'stock': 55},
    {'id': 5, 'name': 'Мышь Razer DeathAdder', 'category': 'Периферия', 'price': 4200, 'stock': 80},
]

MOCK_REPORTS = [
    {'id': 1, 'title': 'Продажи за Q1 2025', 'revenue': 12500000, 'orders_count': 847,
     'top_product': 'Ноутбук Dell XPS 15'},
    {'id': 2, 'title': 'Продажи за Q2 2025', 'revenue': 14200000, 'orders_count': 963,
     'top_product': 'Монитор LG 27UK850'},
    {'id': 3, 'title': 'Клиенты по регионам', 'moscow_pct': 42, 'spb_pct': 18, 'other_pct': 40},
]


# ─── Orders ─────────────────────────────────────────────────────────────────

class OrderListView(APIView):
    """
    GET /business/orders/
    Требует: роль с правом read на ресурс orders.
    """
    permission_classes = [IsAuthenticated, CanReadOrders]

    def get(self, request):
        return Response({
            'resource': 'orders',
            'action': 'read',
            'count': len(MOCK_ORDERS),
            'data': MOCK_ORDERS,
        })


class OrderCreateView(APIView):
    """
    POST /business/orders/create/
    Требует: роль с правом create на ресурс orders.
    """
    permission_classes = [IsAuthenticated, CanCreateOrders]

    def post(self, request):
        new_order = {
            'id': len(MOCK_ORDERS) + 1,
            **request.data,
            'status': 'pending',
        }
        return Response({
            'resource': 'orders',
            'action': 'create',
            'detail': 'Заказ успешно создан (mock).',
            'data': new_order,
        }, status=201)


class OrderUpdateView(APIView):
    """
    PUT /business/orders/<id>/update/
    Требует: роль с правом update на ресурс orders.
    """
    permission_classes = [IsAuthenticated, CanUpdateOrders]

    def put(self, request, pk):
        order = next((o for o in MOCK_ORDERS if o['id'] == pk), None)
        if not order:
            return Response({'detail': 'Заказ не найден.'}, status=404)

        updated = {**order, **request.data, 'id': pk}
        return Response({
            'resource': 'orders',
            'action': 'update',
            'detail': f'Заказ #{pk} обновлён (mock).',
            'data': updated,
        })


class OrderDeleteView(APIView):
    """
    DELETE /business/orders/<id>/delete/
    Требует: роль с правом delete на ресурс orders.
    """
    permission_classes = [IsAuthenticated, CanDeleteOrders]

    def delete(self, request, pk):
        order = next((o for o in MOCK_ORDERS if o['id'] == pk), None)
        if not order:
            return Response({'detail': 'Заказ не найден.'}, status=404)

        return Response({
            'resource': 'orders',
            'action': 'delete',
            'detail': f'Заказ #{pk} удалён (mock).',
        }, status=204)


# ─── Products ────────────────────────────────────────────────────────────────

class ProductListView(APIView):
    """
    GET /business/products/
    Требует: роль с правом read на ресурс products.
    """
    permission_classes = [IsAuthenticated, CanReadProducts]

    def get(self, request):
        return Response({
            'resource': 'products',
            'action': 'read',
            'count': len(MOCK_PRODUCTS),
            'data': MOCK_PRODUCTS,
        })


class ProductCreateView(APIView):
    """
    POST /business/products/create/
    Требует: роль с правом create на ресурс products.
    """
    permission_classes = [IsAuthenticated, CanCreateProducts]

    def post(self, request):
        new_product = {'id': len(MOCK_PRODUCTS) + 1, **request.data}
        return Response({
            'resource': 'products',
            'action': 'create',
            'detail': 'Товар успешно создан (mock).',
            'data': new_product,
        }, status=201)


class ProductUpdateView(APIView):
    """
    PUT /business/products/<id>/update/
    Требует: роль с правом update на ресурс products.
    """
    permission_classes = [IsAuthenticated, CanUpdateProducts]

    def put(self, request, pk):
        product = next((p for p in MOCK_PRODUCTS if p['id'] == pk), None)
        if not product:
            return Response({'detail': 'Товар не найден.'}, status=404)

        updated = {**product, **request.data, 'id': pk}
        return Response({
            'resource': 'products',
            'action': 'update',
            'detail': f'Товар #{pk} обновлён (mock).',
            'data': updated,
        })


class ProductDeleteView(APIView):
    """
    DELETE /business/products/<id>/delete/
    Требует: роль с правом delete на ресурс products.
    """
    permission_classes = [IsAuthenticated, CanDeleteProducts]

    def delete(self, request, pk):
        product = next((p for p in MOCK_PRODUCTS if p['id'] == pk), None)
        if not product:
            return Response({'detail': 'Товар не найден.'}, status=404)

        return Response({
            'resource': 'products',
            'action': 'delete',
            'detail': f'Товар #{pk} удалён (mock).',
        }, status=204)


# ─── Reports ─────────────────────────────────────────────────────────────────

class ReportListView(APIView):
    """
    GET /business/reports/
    Требует: роль с правом read на ресурс reports.
    viewer не имеет доступа → 403.
    """
    permission_classes = [IsAuthenticated, CanReadReports]

    def get(self, request):
        return Response({
            'resource': 'reports',
            'action': 'read',
            'count': len(MOCK_REPORTS),
            'data': MOCK_REPORTS,
        })
