# Fight Night Tickets — Сервис продажи билетов на спортивные мероприятия 🥊

Полноценная production-ready система продажи электронных билетов для РФ.  
Оплата через YooKassa, PDF-билеты с QR-кодами, email-уведомления, мобильный сканер для check-in.

---

## Выбор стека: Django (обоснование)

| Критерий | FastAPI | **Django** ✓ |
|---|---|---|
| Встроенная админка | ❌ нужно писать | ✅ django-admin + unfold |
| Auth + 2FA | ❌ нужно ставить | ✅ allauth + django-otp |
| CSRF защита | ручная | ✅ встроена |
| ORM + Migrations | SQLAlchemy + Alembic | ✅ Django ORM + makemigrations |
| Скорость MVP | медленнее | ✅ быстрее |
| Celery | хорошо | ✅ хорошо |

**Вывод:** для MVP с богатой админкой и коротким дедлайном Django — лучший выбор.

---

## Архитектура системы

```
Browser/Mobile
      │
      ▼
 Nginx (SSL, rate limit)
      │
      ├── /static/*  → WhiteNoise
      │
      ├── Django (Gunicorn 4 workers)
      │      ├── Landing (SSR Jinja2/Django templates)
      │      ├── Order flow (form → YooKassa redirect)
      │      ├── Webhook endpoint (fast 200, defer to Celery)
      │      ├── Check-in scanner (JS QR scanner, mobile)
      │      ├── Admin (django-unfold)
      │      └── Documents (legal pages)
      │
      ├── PostgreSQL (RU-hosted)
      │
      ├── Redis (Celery broker + cache + sessions)
      │
      └── Celery Workers
             ├── Queue: payments  (webhook processing)
             ├── Queue: emails    (SMTP delivery)
             └── Celery Beat      (retry failed emails)

YooKassa API → POST /webhook/ → WebhookEvent → Celery → Order → Ticket → Email
```

---

## Структура проекта

```
project/
├── apps/
│   ├── accounts/      # User (staff + checkers)
│   ├── core/          # TimestampedModel, middleware, context_processors
│   ├── events/        # Event, TicketType, PromoCode
│   ├── orders/        # Customer, Order, Ticket, ConsentLog
│   ├── payments/      # Payment, WebhookEvent, YooKassa service
│   ├── notifications/ # EmailLog, send service
│   ├── checkin/       # CheckInLog, validation service, QR scanner
│   └── documents/     # DocumentPage (юридические страницы)
├── config/
│   ├── settings/{base,development,production}.py
│   ├── celery.py
│   └── urls.py
├── tasks/
│   ├── payment_tasks.py   # process_webhook, on_payment_succeeded, generate_ticket_pdf
│   └── email_tasks.py     # send_ticket_email, retry_failed_emails
├── templates/
│   ├── base.html
│   ├── landing/index.html      # Hero, билеты, FAQ, footer с юр. ссылками
│   ├── orders/{create,success}.html
│   ├── checkin/scanner.html    # Камера + ручной ввод
│   ├── emails/{html,txt,admin}
│   └── documents/page.html
├── static/
│   ├── css/main.css    # Premium mobile-first дизайн
│   └── js/main.js
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── requirements/{base,development,production}.txt
├── .env.example
└── manage.py
```

---

## Схема базы данных

### Event
| Поле | Тип | Особенности |
|---|---|---|
| id | UUID PK | auto |
| slug | SlugField | UNIQUE |
| starts_at | DateTimeField | |
| is_published / is_active | Boolean | db_index |

### TicketType
| Поле | Тип | Особенности |
|---|---|---|
| event | FK → Event | CASCADE |
| price | Decimal(10,2) | min=0.01 |
| total_quantity | PositiveInt | |
| sold_quantity | PositiveInt | обновляется атомарно |
| reserved_quantity | PositiveInt | SELECT FOR UPDATE |

`available = total - sold - reserved` — атомарно через `SELECT FOR UPDATE`.

### Order
| Поле | Тип | Особенности |
|---|---|---|
| order_number | CharField | UNIQUE `FN-20241201-00042` |
| status | Enum | pending/paid/canceled/refunded/expired |
| expires_at | DateTimeField | резервирование 15 мин |
| total_amount | Decimal | snapshot на момент заказа |

### Ticket
| Поле | Тип | Особенности |
|---|---|---|
| ticket_number | CharField | UNIQUE `FN-20241201-00042-01` |
| token | CharField(64) | UNIQUE, urlsafe 48 bytes — в QR |
| verify_code | CharField(12) | UNIQUE, hex 6 bytes — на билете |
| status | Enum | issued/used/canceled/expired |
| pdf_file | FileField | |

### Payment
| Поле | Тип | Особенности |
|---|---|---|
| yookassa_payment_id | CharField | UNIQUE, db_index |
| status | Enum | pending/succeeded/canceled/refunded |
| raw_response | JSONField | полный ответ YooKassa |

### WebhookEvent
| Поле | Тип | Особенности |
|---|---|---|
| event_id | CharField | UNIQUE — идемпотентность |
| event_type | CharField | payment.succeeded / refund.succeeded |
| raw_body | JSONField | полный payload |
| status | Enum | received/processed/failed/skipped |

### Остальные модели
- **Customer** — ФИО, email, phone, consent_given_at, consent_ip
- **ConsentLog** — аудит согласий (ФЗ-152)
- **CheckInLog** — каждое сканирование (token, result, scanned_by, timestamp)
- **EmailLog** — статус доставки, retry_count
- **PromoCode** — fixed/percent скидки, лимиты, даты действия
- **DocumentPage** — юридические страницы через админку

---

## API Endpoints

| Метод | URL | Описание | Auth |
|---|---|---|---|
| GET | `/` | Лендинг | Public |
| GET/POST | `/orders/buy/<id>/` | Форма + создание заказа | Public |
| GET | `/orders/success/` | Страница успеха | Public |
| GET | `/orders/ticket/<token>/` | Просмотр билета | Public |
| POST | `/payments/webhook/yookassa/` | YooKassa webhook | IP + Idempotency |
| GET | `/checkin/` | QR-сканер | Staff/Checker |
| POST | `/checkin/validate/` | AJAX валидация токена | Staff/Checker |
| GET | `/checkin/verify/<token>/` | Публичная страница билета | Public |
| POST | `/api/v1/orders/promo/validate/` | Проверить промокод | Public |
| GET | `/documents/<slug>/` | Юридические страницы | Public |
| GET | `/admin/` | Администратор | Staff + 2FA |

---

## Полная последовательность обработки

```
1. GET /                     → Лендинг с типами билетов
2. Клик "Купить"             → GET /orders/buy/<id>/
3. POST /orders/buy/<id>/    → Validate form
   └─ SELECT FOR UPDATE TicketType (защита от overselling)
   └─ reserved_quantity += quantity
   └─ Order(status=pending, expires_at=+15min)
   └─ ConsentLog created (ФЗ-152 аудит)
   └─ YooKassa.create_payment() → confirmation_url
4. redirect → YooKassa payment page
5. User pays
6. YooKassa → POST /payments/webhook/yookassa/
   └─ WebhookEvent.create() (проверка event_id — идемпотентность)
   └─ return HTTP 200 немедленно
   └─ process_webhook.delay(event_id)
7. Celery: process_webhook_event()
   └─ SELECT FOR UPDATE Payment (защита от двойной обработки)
   └─ Payment.status = succeeded, paid_at = now()
   └─ Order.status = paid
   └─ TicketType.sold += qty, reserved -= qty
   └─ on_payment_succeeded.delay(order_id)
8. Celery: on_payment_succeeded()
   └─ Ticket.create() × quantity (token + verify_code)
   └─ generate_ticket_pdf.delay(ticket_id)
9. Celery: generate_ticket_pdf()
   └─ ReportLab → branded PDF (A5, QR, ФИО, реквизиты)
   └─ ticket.pdf_file.save()
   └─ send_ticket_email.delay(ticket_id)
10. Celery: send_ticket_email()
    └─ EmailMultiAlternatives (HTML + TXT + PDF вложение)
    └─ EmailLog.status = sent
    └─ Admin notification
11. Пользователь открывает PDF → QR-код
12. На входе: Оператор → GET /checkin/ (мобильный браузер)
    └─ Камера сканирует QR
    └─ POST /checkin/validate/ {token}
    └─ SELECT FOR UPDATE Ticket
    └─ issued → status=used → result: "✓ Действителен"
    └─ used   → result: "Уже использован"
    └─ CheckInLog created
```

---

## Обязательные юридические страницы (РФ)

| Slug | Страница | Требование |
|---|---|---|
| `offer` | Публичная оферта | ФЗ о защите прав потребителей |
| `privacy` | Политика конфиденциальности | ФЗ-152 |
| `consent` | Согласие на обработку ПД | ФЗ-152 ст.9 |
| `refund` | Правила возврата | Обязательно |
| `legal` | Реквизиты ИП/ООО (ИНН, ОГРН, адрес) | Обязательно |
| `cookies` | Политика cookies | Рекомендуется |
| `delivery` | Доставка и оплата билета | Обязательно |

**Footer обязательно содержит:**
- Наименование, ИНН, ОГРН/ОГРНИП
- Юридический/фактический адрес
- Email и телефон поддержки
- Все ссылки на юридические страницы
- Copyright + информация о платёжной системе

**Форма заказа обязательно содержит:**
- Чекбокс: согласие с офертой + обработка ПД ✅
- Ссылки на документы — до нажатия "Оплатить" ✅

---

## Безопасность

| Угроза | Защита |
|---|---|
| SQL injection | Django ORM (параметризованные запросы) |
| XSS | Django auto-escape в шаблонах |
| CSRF | CsrfViewMiddleware на всех формах |
| Overselling | `SELECT FOR UPDATE` на TicketType |
| Двойная обработка webhook | `SELECT FOR UPDATE` на Payment + unique event_id |
| Brute force | django-axes (5 попыток → блок 1 час) |
| Rate limiting | DRF throttle + Nginx limit_req |
| Подделка webhook | IP allowlist + идемпотентность |
| Утечка секретов | `.env` + `.gitignore`, секреты не в коде |
| HTTPS | SECURE_SSL_REDIRECT, HSTS 1 год |
| Кликджекинг | X-Frame-Options: DENY |
| Admin brute force | 2FA (django-otp) + django-axes |
| Audit trail | WebhookEvent, EmailLog, CheckInLog, ConsentLog |

---

## MVP-план (14 дней)

| Дни | Задачи |
|---|---|
| **1–2** | Настройка: Docker, PostgreSQL, Redis, базовые модели, миграции |
| **3–4** | Лендинг (HTML/CSS), форма заказа, логика резервирования |
| **5–6** | YooKassa: create_payment, webhook endpoint, обработка статусов |
| **7–8** | PDF-генератор (ReportLab), QR-коды, Ticket после оплаты |
| **9–10** | Email-уведомления (шаблоны + Celery), check-in сканер |
| **11–12** | Юридические страницы, footer, чекбоксы, cookie-notice |
| **13–14** | E2E тесты, деплой на VDS в РФ, Sentry, мониторинг |

---

## Быстрый старт

```bash
cp .env.example .env
# Заполнить .env: DB_PASSWORD, YooKassa, SMTP, SECRET_KEY

cd docker && docker-compose up -d
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser

# Сайт:    http://localhost:8000/
# Админка: http://localhost:8000/admin/
# Сканер:  http://localhost:8000/checkin/
```

---

## Хостинг в РФ (ФЗ-152)

| Провайдер | Тип |
|---|---|
| Yandex Cloud | VPS + Managed PG + Object Storage |
| Selectel | VDS + managed PG |
| Timeweb Cloud | VPS + PostgreSQL |

**Чеклист перед запуском:**
- [ ] Сервер и БД в РФ
- [ ] Уведомление Роскомнадзора об операторе ПД
- [ ] Политика конфиденциальности актуализирована
- [ ] YooKassa: реквизиты заполнены в ЛК
- [ ] SSL-сертификат подключён
- [ ] Резервное копирование БД настроено
- [ ] Sentry DSN настроен
- [ ] 2FA включена для admin-аккаунтов
