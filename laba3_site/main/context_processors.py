from .cart import cart_data, wishlist_ids
from .models import Category
from .store import STORE_ADDRESS, STORE_MAP_URL


def shop_context(request):
    return {'nav_categories': Category.objects.all(), 'cart_count': sum(cart_data(request).values()),
            'wishlist_ids': wishlist_ids(request), 'store_address': STORE_ADDRESS,
            'store_map_url': STORE_MAP_URL}
