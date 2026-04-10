---
name: django-postgresql
description: Guidelines and best practices for developing professional Django applications using PostgreSQL as the database.
---

# Django & PostgreSQL Professional Development

## Objectives
- Ensure a robust and scalable Django architecture.
- Optimize database interactions using PostgreSQL.
- Maintain secure and manageable configurations.

## Guidelines

### 1. Project Configuration & Environment Variables
- Always use environment variables for sensitive settings like `SECRET_KEY`, `DEBUG`, and database credentials. Use packages like `django-environ` or `python-decouple`.
- Configure the database using a database URL format if possible, e.g., `DATABASE_URL=postgres://user:password@host:port/dbname`, using `dj-database-url` or similar.

### 2. PostgreSQL Best Practices in Django
- Install `psycopg2-binary` (for development) or `psycopg[binary]` (PostgreSQL adapter, recommended for Django 4.2+).
- Set the database engine to `'django.db.backends.postgresql'`.
- Take advantage of PostgreSQL-specific fields and indexes provided by `django.contrib.postgres` (e.g., `ArrayField`, `JSONField`, `SearchVectorField`, `GIN` and `GiST` indexes).

### 3. Models and Migrations
- Consider using `UUIDField` as primary keys for models where appropriate, to avoid ID enumeration and for distributed systems.
- Always implement `__str__` methods for your models.
- Set `related_name` explicitly on foreign keys to define clear reverse relationships.
- Create meaningful and small migrations. Do not manually edit migration files unless absolutely necessary.
- Add database indexes (`db_index=True` or `models.Index` in `Meta`) for frequently queried or filtered fields.

### 4. ORM Optimization
- Use `select_related()` for foreign key and one-to-one relationships to avoid N+1 query problems.
- Use `prefetch_related()` for many-to-many and reverse foreign key relationships.
- Use `values()`, `values_list()`, or `only()`/`defer()` when you only need specific columns to reduce memory overhead and speed up queries.
- Leverage database transactions correctly (`transaction.atomic()`) for multi-step data updates to ensure data integrity.

### 5. Security & Performance
- In production, configure connection pooling (e.g., via `pgBouncer`). Within Django, consider setting `CONN_MAX_AGE` (e.g., `600`) in the `DATABASES` setting to persist database connections across requests.
- Always keep `DEBUG = False` in production.
- Ensure proper configuration of `ALLOWED_HOSTS` and CORS settings.

### 6. Authentication & Frontend Communication (JWT)
- Implement stateless, token-based authentication using **JSON Web Tokens (JWT)** for all frontend-backend communication.
- Use libraries like `djangorestframework-simplejwt` to handle JWT generation, validation, and refresh mechanisms.
- Do not rely on Django's session or cookie-based authentication for APIs consumed by decoupled frontends (like React, Next.js, or mobile apps).
- Ensure the frontend stores tokens securely and includes the access token in the `Authorization: Bearer <token>` header for protected resource requests.

## Tools and Scripts
- Use `python manage.py inspectdb` if you are ever integrating with existing PostgreSQL schemas.
- Use `python manage.py dbshell` to access the PostgreSQL command-line client (`psql`) directly.
- For profiling SQL queries locally, consider using `django-debug-toolbar`.
