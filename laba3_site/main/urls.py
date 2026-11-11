from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('collection', views.catalog, name='catalog'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('product', RedirectView.as_view(pattern_name='catalog', permanent=False)),
    path('cart', views.cart, name='cart'),
    path('cart/<int:pk>/', views.cart_action, name='cart_action'),
    path('checkout', views.checkout, name='checkout'),
    path('order/<uuid:token>/', views.order_success, name='order_success'),
    path('wishlist', views.wishlist, name='wishlist'),
    path('wishlist/<int:pk>/', views.wishlist_toggle, name='wishlist_toggle'),
    path('login', LoginView.as_view(template_name='shop/auth.html', redirect_authenticated_user=True), name='login'),
    path('logout', LogoutView.as_view(), name='logout'),
    path('register', views.register, name='register'),
    path('profile', views.profile, name='profile'),
    path('contact', views.contact, name='contact'),
    path('about-us', views.contact, name='about'),
]
