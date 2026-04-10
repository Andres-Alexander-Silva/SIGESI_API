# Guía de Arquitectura del Proyecto (Carpeta `apps`)

Este documento establece las normativas, estructura y patrones arquitectónicos adoptados para el desarrollo dentro del directorio `apps`. Está enfocado en garantizar un código altamente cohesivo, escalable y mantenible para el proyecto, tomando como referencia el contexto delimitado por la aplicación central (por ejemplo, `apps/sigesi` o equivalente).

## 1. Principios Arquitectónicos Base

1. **Modularidad Estricta:** Todo el código de dominio y la lógica de negocio deben vivir dentro de un módulo central bajo `apps/` (por default `apps/sigesi`). No se deben crear aplicaciones Django diseminadas por el proyecto.
2. **Separación de Responsabilidades:** 
   - La validación de datos de entrada/salida recae única y exclusivamente en los **`serializers/`**.
   - La orquestación y las respuestas HTTP recaen en las **`views/`**.
   - Los permisos de acceso se encapsulan en **`permissions.py`** y los **`decorators/`**.
   - El enrutamiento no debe ser monolítico, sino que se divide lógicamente en la carpeta **`routers/`**.

## 2. Estructura de Directorios Requerida

El ecosistema arquitectónico dentro del directorio principal del módulo debe seguir esta estandarización obligatoria:

```plaintext
apps/
├── [app_principal]/    # Aplicación principal del dominio (ej: 'sigesi')
│   ├── models.py       # Definición exhaustiva de entidades (Capa de datos)
│   ├── permissions.py  # Reglas de negocio para autorización y roles de usuario
│   ├── decorators/     # Decoradores personalizados para endpoints y servicios
│   ├── middlewares/    # Interceptores a nivel de aplicación (ej. Contexto JWT)
│   ├── routers/        # Directorios de enrutamiento modulares agrupados por entidad
│   ├── serializers/    # Transformadores, DTOs y lógica de validación de negocio
│   ├── templates/      # Archivos de vista (HTML, reportes, correos electrónicos)
│   ├── utils/          # Helpers, handlers de tokens, envíos de correo, lógicas transversales
│   └── views/          # Módulos de vistas separados lógicamente por entidades/endpoints
└── services/           # (Opcional en la raíz apps/) Capas de integración y clientes para APIs externas
```

## 3. Descripción y Reglas por Componente

### Capa de Datos (`models.py`)
- Se favorece la creación y mantenimiento del esquema en un único archivo consolidado por aplicación. 
- Deben incluir representaciones lógicas consistentes (`__str__`) explícitas, así como subclases `Meta` con los nombres precisos de las tablas de base de datos relacional. No se aceptan modelos anémicos.

### Capa de Presentación / Controladores (`views/`)
- **Prohibido:** Un archivo `views.py` extenso. 
- Cada entidad o modelo lógico debe tener su propia vista o conjunto de vistas separadas en archivos individuales dentro del directorio `views/` y agrupadas en subcarpetas si ameritan. 
- Todas las salidas se enmarcan en **Django Rest Framework (DRF)** utilizando funciones decoradas (`@api_view`) acompañadas de Open API specifications (ej: `drf-yasg` o `drf-spectacular`).

### Capa de Validación (`serializers/`)
- Cualquier tipo de input proveniente del frontend, antes de interactuar con la base de datos o lógica pesada, debe ser instanciado y verificado por medio de un serializador (`serializers.Serializer` o `serializers.ModelSerializer`).
- Aquí residen los validadores a nivel de campo o de objeto general.

### Capa de Enrutamiento (`routers/`)
- Mantiene las rutas abstraídas e independientes. Dentro de `routers/`, se crean carpetas o archivos que mapeen de forma directa 1-a-1 hacia las vistas. Dichos archivos definen localmente su propio árbol de `urlpatterns`.

### Capa de Servicios (`services/` y `utils/`)
- Toda lógica "pesada" que no sea puramente una validación (`serializer`) ni responder un HTTP request (`view`), como la manipulación de JWT estricta o llamadas a proveedores externos, debe delegarse a una clase Helper en `utils` o a un Servicio en `services/`. Esto en pos de mantener el Controlador delgado.

## 4. Patrones de Diseño Implementados

- **Service Layer Pattern (Capa de Servicio):** Consiste en separar lógicas de terceros y código complejo en directorios abstractos (`services/`, `utils/`) para evitar el acoplamiento duro entre controladores y lógica externa, haciendo el backend agnóstico.
- **Data Transfer Object (DTO):** Patrón abstraído detrás del fuerte uso de Serializadores DRF tanto para Ingress (`RequestSerializer`) como Egress (`ResponseSerializer`), garantizando una tipificación consistente orientada al front-end.
- **RESTful Architecture:** Todo controlador debe acatar en nombramiento y acciones a la arquitectura REST, utilizando códigos formales HTTP, validaciones puras y verbos idóneos.
