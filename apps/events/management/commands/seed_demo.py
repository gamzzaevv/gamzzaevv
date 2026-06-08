"""
Заполняет базу демонстрационными данными:
  - два дня боёв (13 и 14 июня) по 50 мест на каждый;
  - юридические страницы (оферта, политика, согласие и т.д.).

Запуск:
    python manage.py seed_demo

Команда идемпотентна — повторный запуск не создаёт дубликаты.
"""
import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.documents.models import DocumentPage
from apps.events.models import Event, TicketType


class Command(BaseCommand):
    help = "Создаёт демо-данные: два дня боёв и юридические страницы."

    def add_arguments(self, parser):
        parser.add_argument(
            "--year",
            type=int,
            default=timezone.now().year,
            help="Год для дат боёв (по умолчанию — текущий).",
        )

    def handle(self, *args, **options):
        year = options["year"]
        self._seed_events(year)
        self._seed_documents()
        self.stdout.write(self.style.SUCCESS("\nГотово! Откройте http://localhost:8000/"))

    # ──────────────────────────────────────────────────────────────
    def _seed_events(self, year: int):
        common = dict(
            venue_name="СК Олимпийский",
            venue_address="Москва, Олимпийский просп., 16",
            venue_city="Москва",
            is_published=True,
            is_active=True,
            fighter_name="Боец 1",
            opponent_name="Боец 2",
        )
        days = [
            dict(
                slug="fight-night-day-1",
                title="Fight Night — День 1",
                starts_at=timezone.make_aware(datetime.datetime(year, 6, 13, 18, 0)),
                short_description="Первый день турнира",
                description="Первый день главного боя сезона. Открывающие поединки.",
            ),
            dict(
                slug="fight-night-day-2",
                title="Fight Night — День 2",
                starts_at=timezone.make_aware(datetime.datetime(year, 6, 14, 18, 0)),
                short_description="Финальный день турнира — главный бой",
                description="Второй, решающий день турнира. Главный бой вечера.",
            ),
        ]

        for d in days:
            event, created = Event.objects.get_or_create(
                slug=d["slug"], defaults={**common, **d}
            )
            verb = "создан" if created else "уже есть"
            self.stdout.write(f"Событие {verb}: {event.title} — {event.starts_at:%d.%m.%Y %H:%M}")

            tt, tt_created = TicketType.objects.get_or_create(
                event=event,
                name="Билет на день",
                defaults=dict(
                    description="Полный доступ на весь день турнира",
                    price="2500.00",
                    total_quantity=50,
                    sort_order=1,
                    is_visible=True,
                ),
            )
            tt_verb = "создан" if tt_created else "уже есть"
            self.stdout.write(f"  Тип билета {tt_verb}: {tt.name} — {tt.total_quantity} мест, {tt.price} ₽")

    # ──────────────────────────────────────────────────────────────
    def _seed_documents(self):
        today = datetime.date.today()
        pages = [
            ("privacy", "Политика конфиденциальности",
             "<h2>1. Общие положения</h2><p>Обработка персональных данных в соответствии с ФЗ-152.</p>"),
            ("terms", "Пользовательское соглашение",
             "<h2>1. Предмет соглашения</h2><p>Условия использования сервиса продажи билетов.</p>"),
            ("refund", "Правила возврата",
             "<h2>Возврат билетов</h2><p>Возврат по Закону о защите прав потребителей.</p>"),
            ("offer", "Публичная оферта",
             "<h2>Публичная оферта</h2><p>Документ является публичной офертой (ст. 437 ГК РФ).</p>"),
            ("consent", "Согласие на обработку ПД",
             "<h2>Согласие</h2><p>Нажимая кнопку, вы даёте согласие на обработку персональных данных.</p>"),
            ("legal", "Реквизиты",
             "<h2>Реквизиты</h2><p>ООО «Файт Найт», ИНН: 7700000000, ОГРН: 1234567890123.</p>"),
            ("cookies", "Политика cookies",
             "<h2>Cookies</h2><p>Сайт использует файлы cookie для корректной работы.</p>"),
            ("delivery", "Доставка и оплата",
             "<h2>Доставка и оплата</h2><p>Билет приходит на email в формате PDF после оплаты.</p>"),
        ]
        for slug, title, content in pages:
            obj, created = DocumentPage.objects.get_or_create(
                slug=slug,
                defaults={
                    "title": title,
                    "content": content,
                    "is_published": True,
                    "version": "1.0",
                    "updated_at_display": today,
                },
            )
            verb = "создана" if created else "уже есть"
            self.stdout.write(f"Страница {verb}: /{slug}/")
