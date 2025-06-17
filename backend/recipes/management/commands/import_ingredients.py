from django.core.management.base import BaseCommand
from recipes.models import Ingredient
import json


class Command(BaseCommand):
    def handle(self, *args, **options):
        file_path = "../../data/ingredients.json"

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                data = json.load(file)

                ingredients = [
                    Ingredient(
                        name=item["name"],
                        measurement_unit=item["measurement_unit"]
                    )
                    for item in data
                ]

                Ingredient.objects.bulk_create(
                    ingredients, ignore_conflicts=True)

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Импортировано {len(ingredients)} ингредиентов")
                )

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(
                "Файл ingredients.json не найден"))
        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR(
                "Ошибка: Некорректный формат JSON"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Ошибка: {str(e)}"))
