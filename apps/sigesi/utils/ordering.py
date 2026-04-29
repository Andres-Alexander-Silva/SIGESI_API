from rest_framework.filters import OrderingFilter


class MultiFieldOrderingFilter(OrderingFilter):
    """
    Extensión de OrderingFilter que permite mapear un alias legible
    a uno o varios campos reales del modelo.

    Uso en el ViewSet:
        filter_backends = [MultiFieldOrderingFilter]
        ordering_aliases = {
            'nombre': ['last_name', 'first_name'],
            'fecha':  ['created_at'],
        }
        ordering = ['last_name', 'first_name']   # orden por defecto

    Parámetros de query soportados:
        ?ordering=nombre     → order_by('last_name', 'first_name')
        ?ordering=-nombre    → order_by('-last_name', '-first_name')
        ?ordering=fecha      → order_by('created_at')
        ?ordering=-fecha     → order_by('-created_at')

    Si el alias no existe o no se envía el parámetro, aplica el orden
    por defecto definido en `ordering` del ViewSet.
    """

    def get_ordering(self, request, queryset, view):
        param = request.query_params.get(self.ordering_param)

        if not param:
            return self.get_default_ordering(view)

        aliases: dict = getattr(view, 'ordering_aliases', {})
        fields = []

        for term in param.split(','):
            term = term.strip()
            desc = term.startswith('-')
            key  = term.lstrip('-')

            mapped = aliases.get(key)
            if mapped:
                prefix = '-' if desc else ''
                fields.extend(f'{prefix}{f}' for f in mapped)

        # Si ningún alias matcheó, respeta el orden por defecto
        return fields or self.get_default_ordering(view)
