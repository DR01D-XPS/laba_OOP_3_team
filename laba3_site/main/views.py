from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import F, Q, Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from .forms import CheckoutForm, RegistrationForm, QuantityForm
from .models import Category, Product, Order, OrderItem
from .cart import cart_rows, cart_data, wishlist_ids


def home(request):
    categories = Category.objects.annotate(product_count=Count('products')).prefetch_related('products')
    products = Product.objects.filter(stock__gt=0).select_related('category')
    return render(request, 'shop/home.html', {'categories': categories, 'products': products[:8],
                                           'hero': products.filter(category__slug='rings').first()})


def catalog(request):
    products = Product.objects.select_related('category').all()
    selected = request.GET.get('category', '')
    query = request.GET.get('q', '').strip()[:200]
    brand = request.GET.get('brand', '')
    sort = request.GET.get('sort', '')
    if selected:
        products = products.filter(category__slug=selected)
    if query:
        # SQLite's default case folding does not cover Cyrillic. This catalogue
        # has 190 rows; resolve case-insensitive matches before database pagination.
        folded = query.casefold()
        ids = [p.pk for p in products
               if any(folded in text.casefold() for text in (p.name, p.sku, p.brand, p.collection))]
        products = products.filter(pk__in=ids)
    if brand:
        products = products.filter(brand=brand)
    for key, lookup in [('min_price', 'price__gte'), ('max_price', 'price__lte')]:
        try:
            amount = Decimal(request.GET.get(key, ''))
            if amount.is_finite() and 0 <= amount <= Decimal('9999999999'):
                products = products.filter(**{lookup: amount})
        except (InvalidOperation, ValueError):
            pass
    if request.GET.get('in_stock'):
        products = products.filter(stock__gt=0)
    ordering = {'price': ('price', 'pk'), '-price': ('-price', 'pk'), 'name': ('name', 'pk')}
    products = products.order_by(*ordering.get(sort, ('pk',)))
    page = Paginator(products, 12).get_page(request.GET.get('page'))
    params = request.GET.copy()
    params.pop('page', None)
    return render(request, 'shop/catalog.html', {
        'page_obj': page, 'categories': Category.objects.annotate(product_count=Count('products')),
        'brands': Product.objects.exclude(brand='').values_list('brand', flat=True).distinct().order_by('brand'),
        'selected_category': selected, 'selected_brand': brand, 'query': query, 'sort': sort,
        'filter_query': params.urlencode(), 'total_products': Product.objects.count(),
    })


def product_detail(request, pk):
    product = get_object_or_404(Product.objects.select_related('category'), pk=pk)
    variants = Product.objects.filter(sku=product.sku).exclude(pk=pk) if product.sku else Product.objects.none()
    return render(request, 'shop/product.html', {'product': product, 'variants': variants,
        'related': Product.objects.filter(category=product.category).exclude(pk=pk)[:4]})


def safe_next(request, default='cart'):
    target = request.POST.get('next', '')
    return target if url_has_allowed_host_and_scheme(target, {request.get_host()}, require_https=request.is_secure()) else reverse(default)


def cart(request):
    rows, total = cart_rows(request)
    return render(request, 'shop/cart.html', {'rows': rows, 'total': total})


@require_POST
def cart_action(request, pk):
    product = get_object_or_404(Product, pk=pk)
    data = cart_data(request)
    key = str(pk)
    action = request.POST.get('action', 'add')
    if action == 'remove':
        data.pop(key, None)
        messages.success(request, 'Украшение удалено из корзины.')
    else:
        form = QuantityForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Количество должно быть целым числом от 1 до 99.')
            return redirect(safe_next(request))
        quantity = form.cleaned_data['quantity']
        if action == 'add':
            quantity += data.get(key, 0)
        if quantity > min(product.stock, 99):
            messages.error(request, f'Доступно в наличии: {product.stock} шт.')
            return redirect(safe_next(request))
        data[key] = quantity
        messages.success(request, 'Корзина обновлена.' if action == 'update' else 'Украшение добавлено в корзину.')
    request.session['cart'] = data
    return redirect(safe_next(request))


def wishlist(request):
    return render(request, 'shop/wishlist.html', {'products': Product.objects.filter(pk__in=wishlist_ids(request)).select_related('category')})


@require_POST
def wishlist_toggle(request, pk):
    get_object_or_404(Product, pk=pk)
    ids = wishlist_ids(request)
    if pk in ids:
        ids.remove(pk)
        messages.success(request, 'Украшение удалено из избранного.')
    else:
        ids.append(pk)
        messages.success(request, 'Украшение добавлено в избранное.')
    request.session['wishlist'] = ids
    return redirect(safe_next(request, 'wishlist'))


def checkout(request):
    rows, total = cart_rows(request)
    if not rows:
        messages.info(request, 'Сначала добавьте украшение в корзину.')
        return redirect('catalog')
    initial = {'name': request.user.get_full_name() or request.user.username, 'email': request.user.email} if request.user.is_authenticated else {}
    form = CheckoutForm(request.POST if request.method == 'POST' else None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                items = []
                locked = Product.objects.select_for_update().filter(pk__in=[r['product'].pk for r in rows]).in_bulk()
                if len(locked) != len(rows):
                    raise ValueError('Состав каталога изменился. Проверьте корзину.')
                total = Decimal('0')
                for row in rows:
                    product = locked[row['product'].pk]
                    quantity = row['quantity']
                    if not Product.objects.filter(pk=product.pk, stock__gte=quantity).update(stock=F('stock') - quantity):
                        raise ValueError(f'Для «{product.name}» недостаточно остатка. Проверьте корзину.')
                    total += product.price * quantity
                    items.append((product, quantity))
                order = Order.objects.create(user=request.user if request.user.is_authenticated else None,
                    total=total, **{k: form.cleaned_data[k] for k in ('name', 'email', 'phone', 'comment')})
                OrderItem.objects.bulk_create([OrderItem(order=order, product=p, name=p.name, sku=p.sku,
                    variant=p.variant, price=p.price, quantity=q) for p, q in items])
            request.session['cart'] = {}
            request.session['order_tokens'] = (request.session.get('order_tokens', []) + [str(order.token)])[-30:]
            return redirect('order_success', token=order.token)
        except ValueError as error:
            form.add_error(None, str(error))
    return render(request, 'shop/checkout.html', {'form': form, 'rows': rows, 'total': total})


def order_success(request, token):
    owned = Q(token__in=request.session.get('order_tokens', []))
    if request.user.is_authenticated:
        owned |= Q(user=request.user)
    order = get_object_or_404(Order.objects.filter(owned).prefetch_related('items__product'), token=token)
    return render(request, 'shop/order.html', {'order': order})


def register(request):
    if request.user.is_authenticated:
        return redirect('profile')
    form = RegistrationForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, 'Аккаунт создан. Добро пожаловать!')
        return redirect('profile')
    return render(request, 'shop/auth.html', {'form': form, 'register': True})


@login_required
def profile(request):
    return render(request, 'shop/profile.html', {'orders': Order.objects.filter(user=request.user).prefetch_related('items')})


def contact(request):
    return render(request, 'shop/contact.html')
