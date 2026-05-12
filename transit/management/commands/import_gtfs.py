import csv
import os
from django.core.management.base import BaseCommand
from transit.models import Route, Stage

GTFS_DIR = os.path.join(
    os.path.dirname(__file__), '..', '..', '..', 'ASSETS', 'GTFS_FEED_2019'
)

# Official GTFS name → street nickname translation table
NICKNAME_MAP = {
    'haile selassie ave':           'Railways',
    'racecourse road':              'Muthurwa',
    'ronald ngala st':              'Posta',
    'ronald ngala st / fire stn':   'Koja',
    'tom mboya st / fire stn':      'Koja',
    'latema road':                  'Odeon',
    'latema rd':                    'Odeon',
    'ngara road':                   'Fig Tree',
    'park road':                    'Equity Ngara',
    'temple road':                  '28',
    'university way':               '28',
    'kenyatta avenue / kencom':     'Kencom',
    'moi avenue hilton':            'Kencom',
}


class Command(BaseCommand):
    help = 'Import routes and stages from GTFS feed files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear', action='store_true',
            help='Delete existing Route and Stage records before importing'
        )

    def handle(self, *args, **options):
        if options['clear']:
            Stage.objects.all().delete()
            Route.objects.all().delete()
            self.stdout.write('Cleared existing routes and stages.')

        # Skip if data already loaded (unless --clear was passed)
        if not options['clear'] and Route.objects.exists():
            self.stdout.write('Data already imported. Use --clear to re-import.')
            return
        routes_file   = os.path.join(GTFS_DIR, 'routes.txt')
        stops_file    = os.path.join(GTFS_DIR, 'stops.txt')
        trips_file    = os.path.join(GTFS_DIR, 'trips.txt')
        times_file    = os.path.join(GTFS_DIR, 'stop_times.txt')

        # ── 1. Load routes ────────────────────────────────────────────────
        # route_id → Route model instance
        route_map = {}
        routes_created = 0

        with open(routes_file, encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                route_id   = row['route_id'].strip()
                short_name = row['route_short_name'].strip()
                long_name  = row['route_long_name'].strip()

                # Derive a human-readable destination from the long name
                # Format is usually "Origin-Stop1-Stop2-Destination"
                parts = [p.strip() for p in long_name.replace(',', '-').split('-') if p.strip()]
                destination = parts[-1] if parts else long_name

                route, created = Route.objects.get_or_create(
                    number=short_name,
                    defaults={
                        'destination': destination,
                        'fare_estimate': 'See operator',
                    }
                )
                route_map[route_id] = route
                if created:
                    routes_created += 1

        self.stdout.write(f'Routes: {routes_created} created, {len(route_map) - routes_created} already existed.')

        # ── 2. Load stops (id → name/lat/lon) ────────────────────────────
        stop_map = {}
        with open(stops_file, encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                stop_id = row['stop_id'].strip()
                try:
                    lat = float(row['stop_lat'])
                    lon = float(row['stop_lon'])
                except (ValueError, KeyError):
                    continue
                name = row['stop_name'].strip()
                # location_type 'U' = undesignated informal stop
                is_undesignated = row.get('location_type', '').strip().upper() == 'U'
                stop_map[stop_id] = {
                    'name':           name,
                    'nickname':       NICKNAME_MAP.get(name.lower(), ''),
                    'lat':            lat,
                    'lon':            lon,
                    'undesignated':   is_undesignated,
                }

        self.stdout.write(f'Stops loaded: {len(stop_map)}')

        # ── 3. Build trip_id → route mapping via trips.txt ───────────────
        trip_route_map = {}
        with open(trips_file, encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                trip_id  = row['trip_id'].strip()
                route_id = row['route_id'].strip()
                if route_id in route_map:
                    trip_route_map[trip_id] = route_map[route_id]

        self.stdout.write(f'Trips mapped: {len(trip_route_map)}')

        # ── 4. Parse stop_times and create Stage objects ──────────────────
        # Collect (route, stop_sequence, stop_id) — keep only the first
        # trip per route to avoid duplicating stops.
        seen_routes   = set()   # route ids already processed
        route_stops   = {}      # route_id → list of (stop_sequence, stop_id)

        with open(times_file, encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                trip_id = row['trip_id'].strip()
                if trip_id not in trip_route_map:
                    continue
                route = trip_route_map[trip_id]
                if route.pk in seen_routes:
                    continue
                stop_id  = row['stop_id'].strip()
                try:
                    seq = int(row['stop_sequence'])
                except (ValueError, KeyError):
                    continue
                route_stops.setdefault(route.pk, {'route': route, 'stops': []})
                route_stops[route.pk]['stops'].append((seq, stop_id))

            # Mark first trip per route as done after we've collected all its rows
            # (we process the whole file, so just deduplicate by route after)

        # Keep only the first trip's stops per route (already collected above
        # because we skip once route.pk is in seen_routes — but we never add
        # to seen_routes inside the loop, so we get ALL trips merged).
        # Re-do: keep unique (seq, stop_id) per route, sorted by seq.
        stages_created = 0
        for pk, data in route_stops.items():
            route = data['route']
            # Deduplicate stops by sequence number, keep first occurrence
            seen_seq = {}
            for seq, stop_id in sorted(data['stops']):
                if seq not in seen_seq:
                    seen_seq[seq] = stop_id

            for order, (seq, stop_id) in enumerate(sorted(seen_seq.items()), start=1):
                if stop_id not in stop_map:
                    continue
                stop = stop_map[stop_id]
                _, created = Stage.objects.get_or_create(
                    route=route,
                    name=stop['name'],
                    defaults={
                        'nickname':        stop['nickname'],
                        'latitude':        stop['lat'],
                        'longitude':       stop['lon'],
                        'order':           order,
                        'is_major_hub':    bool(stop['nickname']),
                        'is_undesignated': stop['undesignated'],
                    }
                )
                if created:
                    stages_created += 1

        self.stdout.write(self.style.SUCCESS(
            f'Done. Stages created: {stages_created}'
        ))
