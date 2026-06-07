import json

from django.db.models import Count, Q

from apps.sigesi.models import Informe, Semillero


class InformesService:
    """Servicio de generación de informes agregados de un semillero."""

    @staticmethod
    def generar_informe(
        semillero_id: int, tipo: str, semestre: str, usuario,
    ) -> Informe:
        """Genera y persiste un informe con las métricas del semillero.

        Orquesta el cálculo de métricas, la estructuración del contenido y la
        creación de la fila ``Informe``.

        Args:
            semillero_id: ID del semillero a reportar.
            tipo: Tipo de informe (``Informe`` lo expone en su título/campo).
            semestre: Semestre del informe (p. ej. ``'2025-1'``).
            usuario: Usuario que genera el informe (queda en ``generado_por``).

        Returns:
            La instancia ``Informe`` creada.

        Raises:
            ValueError: Si no existe un semillero con ese ID.
        """
        semillero = InformesService._calcular_metricas(semillero_id)
        contenido = InformesService._estructurar_contenido(
            semillero, tipo, semestre)
        return InformesService._persistir_informe(
            semillero, tipo, semestre, contenido, usuario)

    @staticmethod
    def _calcular_metricas(semillero_id: int) -> Semillero:
        """Devuelve el semillero anotado con sus métricas agregadas vía ORM.

        Args:
            semillero_id: ID del semillero a consultar.

        Returns:
            El ``Semillero`` con los atributos anotados ``total_proyectos``,
            ``proyectos_activos``, ``total_matriculas`` y ``total_producciones``.

        Raises:
            ValueError: Si no existe un semillero con ese ID.
        """
        semillero = (
            Semillero.objects.filter(id=semillero_id)
            .annotate(
                total_proyectos=Count('proyectos', distinct=True),
                proyectos_activos=Count(
                    'proyectos',
                    filter=Q(proyectos__estado__in=['en_ejecucion', 'en_resultados']),
                    distinct=True,
                ),
                total_matriculas=Count(
                    'matriculas',
                    filter=Q(matriculas__estado='activa'),
                    distinct=True,
                ),
                total_producciones=Count('producciones', distinct=True),
            )
            .first()
        )
        if not semillero:
            raise ValueError("Semillero no encontrado.")
        return semillero

    @staticmethod
    def _estructurar_contenido(
        semillero: Semillero, tipo: str, semestre: str,
    ) -> dict:
        """Arma el diccionario de contenido (resumen + métricas) del informe."""
        return {
            "resumen_ejecutivo": {
                "semillero": semillero.nombre,
                "codigo": semillero.codigo,
                "semestre": semestre,
                "tipo": tipo,
            },
            "metricas": {
                "total_proyectos": semillero.total_proyectos,
                "proyectos_activos": semillero.proyectos_activos,
                "estudiantes_activos": semillero.total_matriculas,
                "producciones_academicas": semillero.total_producciones,
            },
        }

    @staticmethod
    def _persistir_informe(
        semillero: Semillero, tipo: str, semestre: str, contenido: dict, usuario,
    ) -> Informe:
        """Crea la fila ``Informe`` serializando el contenido a JSON."""
        return Informe.objects.create(
            semillero=semillero,
            titulo=f"Informe {tipo.capitalize()} - {semillero.nombre} ({semestre})",
            tipo=tipo,
            semestre=semestre,
            contenido=json.dumps(contenido, indent=2, ensure_ascii=False),
            estado=Informe.EstadoChoices.GENERADO,
            generado_por=usuario,
        )
