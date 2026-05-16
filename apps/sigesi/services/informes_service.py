import json
from django.db.models import Count, Q
from apps.sigesi.models import Semillero, Informe

class InformesService:
    @staticmethod
    def generar_informe(semillero_id, tipo, semestre, usuario):
        # Gather metrics using ORM
        qs = Semillero.objects.filter(id=semillero_id).annotate(
            total_proyectos=Count('proyectos', distinct=True),
            proyectos_activos=Count('proyectos', filter=Q(proyectos__estado__in=['en_ejecucion', 'en_resultados']), distinct=True),
            total_matriculas=Count('matriculas', filter=Q(matriculas__estado='activa'), distinct=True),
            total_producciones=Count('producciones', distinct=True)
        )
        
        semillero = qs.first()
        if not semillero:
            raise ValueError("Semillero no encontrado.")

        # Structure content
        contenido = {
            "resumen_ejecutivo": {
                "semillero": semillero.nombre,
                "codigo": semillero.codigo,
                "semestre": semestre,
                "tipo": tipo
            },
            "metricas": {
                "total_proyectos": semillero.total_proyectos,
                "proyectos_activos": semillero.proyectos_activos,
                "estudiantes_activos": semillero.total_matriculas,
                "producciones_academicas": semillero.total_producciones
            }
        }

        # Create informe record
        informe = Informe.objects.create(
            semillero=semillero,
            titulo=f"Informe {tipo.capitalize()} - {semillero.nombre} ({semestre})",
            tipo=tipo,
            semestre=semestre,
            contenido=json.dumps(contenido, indent=2, ensure_ascii=False),
            estado=Informe.EstadoChoices.GENERADO,
            generado_por=usuario
        )
        
        return informe
