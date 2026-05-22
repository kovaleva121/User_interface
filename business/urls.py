from django.urls import path
from business.apps import BusinessConfig
from business.views import (
    OrderListView, OrderCreateView, OrderUpdateView, OrderDeleteView,
    ProductListView, ProductCreateView, ProductUpdateView, ProductDeleteView,
    ReportListView,
)

app_name = BusinessConfig.name

urlpatterns = [
    # Orders
    path('orders/', OrderListView.as_view(), name='order_list'),
    path('orders/create/', OrderCreateView.as_view(), name='order_create'),
    path('orders/<int:pk>/update/', OrderUpdateView.as_view(), name='order_update'),
    path('orders/<int:pk>/delete/', OrderDeleteView.as_view(), name='order_delete'),

    # Products
    path('products/', ProductListView.as_view(), name='product_list'),
    path('products/create/', ProductCreateView.as_view(), name='product_create'),
    path('products/<int:pk>/update/', ProductUpdateView.as_view(), name='product_update'),
    path('products/<int:pk>/delete/', ProductDeleteView.as_view(), name='product_delete'),

    # Reports
    path('reports/', ReportListView.as_view(), name='report_list'),
]
