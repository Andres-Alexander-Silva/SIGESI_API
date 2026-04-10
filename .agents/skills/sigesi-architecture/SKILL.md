---
name: sigesi-architecture
description: Provides architectural guidelines and restrictions to ensure all development is strictly contained within the apps/sigesi application, following its established structural patterns.
---

# Sigesi Architecture Skill

Use this skill when developing, refactoring, or adding new features to the project to ensure you respect the current architectural construction. The project is primarily built using Django Rest Framework and the core domain logic resides exclusively within the `apps/sigesi` application.

## Objectives
- Maintain a highly cohesive and decoupled structure by strictly working inside the `apps/sigesi` application.
- Enforce the modular pattern of separate views, routers, utils, decorators, and middleware.
- Ensure consistency in how models, APIs, and business logic are implemented using Django Rest Framework.

## Core Architectural Guidelines

### 1. Strict Scope (`apps/sigesi`)
- **Actionable Rule:** ALL new files, models, views, routers, and logic MUST be implemented under the `apps/sigesi` directory path (`c:\INGENIERIA DE SISTEMAS\VII SEMESTRE\SIGESI_API\SIGESI_API\apps\sigesi`).
- Do not create new Django apps or modify code outside of this application unless explicitly instructed by the user. 
- The entire system's domain is encapsulated within this singular "modularized monolithic" application directory.

### 2. Models (`models.py`)
- **Actionable Rule:** All database models are contained within `apps/sigesi/models.py`.
- Do not create a `models/` directory or split models into multiple files. Keep adding and maintaining models within the single `models.py` file, respecting the existing categorized sections (e.g., SISTEMA DE PERMISOS, USUARIOS, ESTRUCTURA ORGANIZATIVA, etc.).
- Follow existing patterns for `TextChoices`, string representations (`__str__`), and Meta classes.

### 3. Views (`views/` Directory)
- **Actionable Rule:** Do NOT use a monolithic `views.py` file.
- Views must be placed as modular Python files within the `apps/sigesi/views/` directory (e.g., `health.py`, `users.py`).
- Use **Django Rest Framework**. Prefer functional views decorated with `@api_view` and permissions like `@permission_classes` exactly as established in the current codebase, or DRF Class-Based Views if specifically warranted by the module's complexity.

### 4. Routers (`routers/` Directory)
- **Actionable Rule:** URL routing is modularized using the `routers/` directory, acting as decoupled `urls.py` modules.
- Each logical grouping of views should have a corresponding router file inside `apps/sigesi/routers/` (e.g., `health.py` router mapping to `health.py` views).
- Define a `urlpatterns` list in each router file using `django.urls.path`.

### 5. Utilities, Decorators, and Middleware
- **Business Logic & Utilities:** Place reusable helper functions and cross-cutting business logic inside the `apps/sigesi/utils/` directory.
- **Custom Decorators:** Place access control and custom execution wrappers in `apps/sigesi/decorators/`.
- **Middleware:** Place custom request/response processing logic in `apps/sigesi/middleware/`.

## Technology Stack Alignment
- **API Framework:** Django Rest Framework (DRF). Use Response, status, and api_view imports from `rest_framework`.
- **Database:** Assume PostgreSQL backend operations and maintain compatibility. Include `django.db` connections or handles carefully if executing raw queries, although ORM is strictly preferred.

## Reference Architecture
- **Architecture Guidelines:** Always refer to the [arquitectura_apps.md](arquitectura_apps.md) file as an additional guide to understand the specific components layout, internal directory responsibilities, and structural patterns expected within the application module.
