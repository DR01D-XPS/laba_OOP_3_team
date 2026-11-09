from decimal import Decimal, InvalidOperation
from django import template

register = template.Library()


@register.filter
def rub(value):
    try:
        amount = Decimal(value)
        text = f'{amount:,.2f}' if amount % 1 else f'{amount:,.0f}'
        return text.replace(',', '\u00a0').replace('.', ',') + ' ₽'
    except (InvalidOperation, TypeError, ValueError):
        return '—'
