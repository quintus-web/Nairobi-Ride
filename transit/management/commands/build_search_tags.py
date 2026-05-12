from django.core.management.base import BaseCommand
from transit.models import Route


class Command(BaseCommand):
    help = 'Populate search_tags on every Route with all its stage names'

    def handle(self, *args, **kwargs):
        routes = Route.objects.prefetch_related('stages').all()
        for route in routes:
            stage_names = route.stages.values_list('name', flat=True)
            route.search_tags = ', '.join(stage_names)
            route.save(update_fields=['search_tags'])
        self.stdout.write(self.style.SUCCESS(f'Updated search_tags for {routes.count()} routes.'))
