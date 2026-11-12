from pathlib import Path
from decimal import Decimal, InvalidOperation
import hashlib
import unicodedata
import openpyxl
from PIL import Image, ImageOps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from main.models import Category, Product


def normalize(value):
    return unicodedata.normalize('NFC', str(value or '')).strip().replace('\\', '/').casefold()


class Command(BaseCommand):
    help = 'Импорт Excel и фотографий из source_data. Повторный запуск обновляет данные по ID варианта.'

    def add_arguments(self, parser):
        parser.add_argument('--file', default=str(settings.BASE_DIR / 'source_data/каталог.xlsx'))
        parser.add_argument('--images', default=str(settings.BASE_DIR / 'source_data/images'))

    @transaction.atomic
    def handle(self, *args, **options):
        source, image_root = Path(options['file']), Path(options['images'])
        if not source.exists():
            raise CommandError(f'Не найден каталог: {source}')
        slugs = {'Браслеты': 'bracelets', 'Броши': 'brooches', 'Колье': 'necklaces', 'Кольца': 'rings'}
        indexed = {}
        for path in sorted(image_root.rglob('*')):
            if path.suffix.lower() not in ('.jpg', '.jpeg', '.png', '.webp'):
                continue
            parts = path.relative_to(image_root).parts
            for key in (normalize('/'.join(parts[1:-1])), normalize(path.stem)):
                if key:
                    indexed.setdefault(key, path)
        output = settings.MEDIA_ROOT / 'products'
        output.mkdir(parents=True, exist_ok=True)
        workbook = openpyxl.load_workbook(source, read_only=True, data_only=True)
        imported = matched = 0
        missing = []
        for row in workbook.active.iter_rows(min_row=2, values_only=True):
            category, name, serial, brand, collection, price, stock, warehouse, external_id, variant, sku = row[:11]
            if not external_id:
                continue
            cat, _ = Category.objects.get_or_create(name=str(category), defaults={'slug': slugs.get(category, f'category-{imported}')})
            variant = str(variant or '').strip()
            parts = variant.split('/', 1)
            try:
                weight = Decimal(parts[0].strip().replace(',', '.'))
            except InvalidOperation:
                weight = None
            size = parts[1].strip() if len(parts) > 1 else ''
            size = '' if size == '-' else size
            values = dict(category=cat, name=str(name), serial=str(serial or ''), brand=str(brand or ''),
                collection=str(collection or ''), price=Decimal(str(price)), stock=int(stock or 0),
                warehouse=str(warehouse or ''), variant=variant, sku=str(sku or ''), weight=weight, size=size)
            candidates = [normalize(sku)]
            if not sku:
                candidates.append(normalize(str(name).rsplit(' ', 1)[-1]))
            image_path = next((indexed[k] for k in candidates if k in indexed), None)
            if image_path:
                filename = hashlib.sha256(str(image_path.relative_to(image_root)).encode()).hexdigest()[:20] + '.jpg'
                target = output / filename
                if not target.exists():
                    with Image.open(image_path) as image:
                        image = ImageOps.exif_transpose(image).convert('RGB')
                        image.thumbnail((1100, 1100))
                        image.save(target, quality=90, optimize=True)
                values['image'] = 'products/' + filename
                matched += 1
            else:
                missing.append(str(external_id))
            Product.objects.update_or_create(external_id=int(external_id), defaults=values)
            imported += 1
        workbook.close()
        self.stdout.write(self.style.SUCCESS(f'Импортировано: {imported}. С фотографиями: {matched}.'))
        if missing:
            self.stdout.write(self.style.WARNING('Нет фотографии для ID: ' + ', '.join(missing)))
