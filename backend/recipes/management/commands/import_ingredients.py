import json
from pathlib import Path

from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Загрузка ингредиентов из JSON файла'

    def handle(self, *args, **options):
        base_dir = Path(__file__).resolve().parent.parent.parent.parent.parent

        data_file = base_dir / 'data' / 'ingredients.json'

        if not data_file.exists():
            self.stdout.write(self.style.ERROR(
                f'Файл {data_file} не найден'))
            return
        if not data_file.is_file():
            self.stdout.write(self.style.ERROR(
                f'{data_file} не является файлом'))
            return

        try:
            with data_file.open(encoding='utf-8') as file:
                data = json.load(file)

                ingredients = (
                    Ingredient(
                        name=item['name'],
                        measurement_unit=item['measurement_unit']
                    )
                    for item in data
                )

                Ingredient.objects.bulk_create(
                    ingredients, ignore_conflicts=True)

                self.stdout.write(
                    self.style.SUCCESS(
                        f'Импортировано {len(ingredients)} ингредиентов')
                )

        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR(
                'Ошибка: Некорректный формат JSON'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка: {str(e)}'))
