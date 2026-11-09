import uuid
from django.conf import settings
from django.db import models
from django.urls import reverse


class Category(models.Model):
    name = models.CharField('Название', max_length=80, unique=True)
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['id']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('catalog') + '?category=' + self.slug


class Product(models.Model):
    external_id = models.PositiveIntegerField('ID варианта из каталога', unique=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products', verbose_name='Категория')
    name = models.CharField('Название', max_length=500)
    sku = models.CharField('Артикул', max_length=120, blank=True, db_index=True)
    serial = models.CharField('Серия', max_length=100, blank=True)
    brand = models.CharField('Бренд', max_length=160, blank=True, db_index=True)
    collection = models.CharField('Коллекция', max_length=200, blank=True)
    price = models.DecimalField('Цена', max_digits=12, decimal_places=2)
    stock = models.PositiveIntegerField('Остаток', default=0)
    warehouse = models.CharField('Салон', max_length=200, blank=True)
    variant = models.CharField('Вариант из каталога', max_length=150, blank=True)
    weight = models.DecimalField('Вес, г', max_digits=9, decimal_places=3, null=True, blank=True)
    size = models.CharField('Размер', max_length=40, blank=True)
    image = models.ImageField('Фото', upload_to='products/', blank=True)

    class Meta:
        verbose_name = 'Украшение'
        verbose_name_plural = 'Украшения'
        ordering = ['id']
        constraints = [models.CheckConstraint(condition=models.Q(price__gte=0), name='product_price_nonnegative')]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('product_detail', args=[self.pk])


class Order(models.Model):
    class Status(models.TextChoices):
        NEW = 'new', 'Новый'
        CONFIRMED = 'confirmed', 'Подтверждён'
        COMPLETED = 'completed', 'Выдан'
        CANCELLED = 'cancelled', 'Отменён'

    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Покупатель')
    name = models.CharField('Имя', max_length=120)
    email = models.EmailField('Email')
    phone = models.CharField('Телефон', max_length=30)
    comment = models.TextField('Комментарий', blank=True, max_length=1500)
    total = models.DecimalField('Сумма', max_digits=14, decimal_places=2)
    status = models.CharField('Статус', max_length=20, choices=Status.choices, default=Status.NEW)
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']

    def __str__(self):
        return f'Заказ №{self.pk}'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name='Украшение')
    name = models.CharField('Название на момент заказа', max_length=500)
    sku = models.CharField('Артикул', max_length=120, blank=True)
    variant = models.CharField('Вариант', max_length=150, blank=True)
    price = models.DecimalField('Цена за единицу', max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField('Количество')

    @property
    def total(self):
        return self.price * self.quantity
