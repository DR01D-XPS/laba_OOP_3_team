from decimal import Decimal
from .models import Product


def cart_data(request):
    raw = request.session.get('cart', {})
    if not isinstance(raw, dict):
        return {}
    data = {}
    for key, value in raw.items():
        try:
            pk, quantity = int(key), int(value)
            if 0 < pk < 2**63 and 0 < quantity <= 99:
                data[str(pk)] = quantity
        except (TypeError, ValueError, OverflowError):
            pass
    return data


def wishlist_ids(request):
    raw = request.session.get('wishlist', [])
    if not isinstance(raw, list):
        return []
    return list(dict.fromkeys(x for x in raw if isinstance(x, int) and 0 < x < 2**63))[:300]


def cart_rows(request):
    data = cart_data(request)
    rows = []
    for product in Product.objects.filter(pk__in=[int(k) for k in data]).select_related('category'):
        quantity = data[str(product.pk)]
        rows.append({'product': product, 'quantity': quantity, 'subtotal': product.price * quantity,
                     'available': product.stock >= quantity})
    return rows, sum((r['subtotal'] for r in rows), Decimal('0'))
