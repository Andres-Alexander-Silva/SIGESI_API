# Arquitectura de la Carpeta `apps`

Este documento describe la estructura y arquitectura interna del directorio `apps`, el cual contiene las aplicaciones principales y dependencias de negocio para el proyecto _NeoDental Manager API_.

## Estructura de Directorios

La carpeta `apps` está organizada en los siguientes subdirectorios principales:

```plaintext
apps/
├── neodental/          # Aplicación principal de Django
│   ├── apps.py         # Configuración del app
│   ├── models.py       # Definición de los modelos de base de datos
│   ├── permissions.py  # Clases personalizadas de permisos y roles de usuario
│   ├── decorators/     # Decoradores personalizados para vistas/controladores
│   │   └── decorator.py
│   ├── middlewares/    # Custom middlewares para la aplicación
│   │   └── authentication_middleware.py
│   ├── migrations/     # Migraciones de las base de datos
│   ├── routers/        # Configuración de URLs y enrutadores (DRF)
│   │   ├── auth/
│   │   │   └── auth_urls.py
│   │   ├── citas/
│   │   │   └── citas_urls.py
│   │   ├── config/
│   │   │   ├── agenda_urls.py
│   │   │   ├── bloqueo_horario_urls.py
│   │   │   ├── gestion_financiera_urls.py
│   │   │   ├── persona_urls.py
│   │   │   ├── rbac_urls.py
│   │   │   ├── rol_urls.py
│   │   │   ├── tipo_consulta_urls.py
│   │   │   ├── tipo_documento_urls.py
│   │   │   └── usuarios_urls.py
│   │   └── historialClinico/
│   │       └── h_clinico_urls.py
│   ├── serializers/    # Serializadores para las APIs
│   │   ├── auth/
│   │   │   ├── login_serializer.py
│   │   │   ├── logout_serializer.py
│   │   │   └── update_password_serializer.py
│   │   ├── citas/
│   │   │   └── citas_serializer.py
│   │   ├── config/
│   │   │   ├── agenda_serializer.py
│   │   │   ├── bloqueo_horario_serializer.py
│   │   │   ├── gestion_financiera_serializer.py
│   │   │   ├── persona_serializer.py
│   │   │   ├── rbac_serializer.py
│   │   │   ├── rol_serializer.py
│   │   │   ├── tipo_consulta_serializer.py
│   │   │   ├── tipo_documento_serializer.py
│   │   │   └── usuario_serializer.py
│   │   └── historialClinico/
│   │       └── h_clinico_serializer.py
│   ├── templates/      # Plantillas HTML genéricas o de correo
│   │   ├── agenda_cita.html
│   │   └── factura_electronica.html
│   ├── utils/          # Funciones utilitarias y helpers compartidos
│   │   ├── jwt_handler.py
│   │   ├── send_mail.py
│   │   ├── throttles.py
│   │   └── time.py
│   └── views/          # Lógica de la API orientada a las respuestas
│       ├── auth/
│       │   ├── login_view.py
│       │   └── logout_view.py
│       ├── citas/
│       │   └── citas_view.py
│       ├── config/
│       │   ├── agenda_view.py
│       │   ├── bloqueo_horario_view.py
│       │   ├── gestion_financiera_view.py
│       │   ├── persona_view.py
│       │   ├── rbac_view.py
│       │   ├── rol_view.py
│       │   ├── tipo_consulta_view.py
│       │   ├── tipo_documento_view.py
│       │   └── usuarios_view.py
│       └── historialClinico/
│           └── h_clinico_view.py
└── services/           # Lógica de integración de servicios externos
    └── factus_services.py # Integración con la API de "Factus" u otros servicios
```

## Descripción de Componentes

### 1. `neodental/`

Esta es la aplicación Django principal que maneja los recursos transaccionales y operaciones de la clínica/entidad. Sigue una arquitectura limpia orientada hacia las APIs empleando **Django Rest Framework (DRF)**.

- **Models (`models.py`)**: Define el esquema de la base de datos (Entidades principales como pacientes, citas, tratamientos, etc.).
- **Views (`views/`)**: Implementa los endpoints HTTP y maneja la lógica de negocio que responde al cliente.
- **Serializers (`serializers/`)**: Es la capa responsable de transformar la información de los modelos a un formato JSON entendible por el frontend y viceversa para el registro y actualización de datos.
- **Routers (`routers/`)**: Abstrae las configuraciones de URL de manera auto-gestionada para conectar con las ViewSets o las `views`.
- **Permissions (`permissions.py`) & Decorators (`decorators/`) & Middlewares (`middlewares/`)**: Encargados de la verificación de autorizaciones y validación del acceso a los recursos de manera global o a nivel de endpoint.

### 2. `services/`

A diferencia de `neodental`, la carpeta `services` abstrae lógicas de terceros que no conciernen a los modelos o la API de forma directa (Separación de Responsabilidades o Patrón Service Layer).

- **Factus Services (`factus_services.py`)**: Archivo destinado a la comunicación o integración con APIs externas u operaciones complejas y transaccionales como facturación.

## Patrones de Diseño Detectados

- **Model-View-Controller/Model-View-Template (MVC/MVT):** Estructura base de Django.
- **Service Layer Pattern:** Movimiento evidente de la lógica relacionada al consumo de servicios y procesos pesados ajenos a la Vista hacia la carpeta de `services/`.
- **Clean Architecture (Approximation):** Separación de la validación de Payload (`serializers`) y la autorización (`permissions`), manteniendo la lógica de ruteo (`routers`) aislada.
