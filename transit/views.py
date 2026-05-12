from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db import models as db_models
from .models import Route, Stage, Contribution

# Smart location aliases — maps user-friendly terms to actual stage name fragments
LOCATION_ALIASES = {
    'cbd':         ['kencom', 'ambassador', 'railways', 'koja', 'odeon', 'muthurwa', 'bus station', 'tusker'],
    'town':        ['kencom', 'ambassador', 'railways', 'koja', 'odeon', 'muthurwa', 'bus station'],
    'city centre': ['kencom', 'ambassador', 'railways', 'koja', 'odeon', 'muthurwa'],
    # Slang / street nicknames
    'mchwak':      ['mwiki'],
    'kanairo':     ['nairobi'],
    '28':          ['temple road', 'university way'],
    'fig tree':    ['ngara'],
    'posta':       ['ronald ngala', 'posta'],
    'equity ngara':['park road', 'ngara'],
    'kencom':      ['kencom', 'haile selassie', 'kenyatta avenue'],
    'railways':    ['railways', 'haile selassie'],
    'muthurwa':    ['muthurwa', 'racecourse'],
    'koja':        ['koja', 'khoja', 'tom mboya', 'fire stn'],
    'odeon':       ['odeon', 'latema', 'tusker'],
}

CBD_HUBS = [
    {'name': 'Kencom', 'lat': -1.2833, 'lng': 36.8219},
    {'name': 'Ambassador', 'lat': -1.2864, 'lng': 36.8230},
    {'name': 'Railways', 'lat': -1.2921, 'lng': 36.8219},
    {'name': 'Odeon', 'lat': -1.2847, 'lng': 36.8264},
    {'name': 'Koja', 'lat': -1.2800, 'lng': 36.8350},
    {'name': 'Muthurwa', 'lat': -1.2836, 'lng': 36.8389},
]


def _resolve_aliases(term):
    """Return list of stage name fragments to search, expanding aliases like 'cbd'."""
    return LOCATION_ALIASES.get(term.lower(), [term])


def _routes_for_term(term):
    """Return a queryset of routes matching a term, with alias expansion."""
    fragments = _resolve_aliases(term)
    q = db_models.Q()
    for frag in fragments:
        q |= db_models.Q(stages__name__icontains=frag)
        q |= db_models.Q(stages__nickname__icontains=frag)
        q |= db_models.Q(search_tags__icontains=frag)
    q |= db_models.Q(number__icontains=term)
    q |= db_models.Q(destination__icontains=term)
    q |= db_models.Q(sacco__icontains=term)
    return Route.objects.filter(q).distinct()


def home(request):
    origin      = request.GET.get('origin', '').strip()
    destination = request.GET.get('destination', '').strip()
    query       = request.GET.get('q', '').strip()
    results     = None

    is_cbd_search = origin.lower() in LOCATION_ALIASES
    cbd_hubs      = CBD_HUBS if is_cbd_search else []

    if origin and destination:
        origin_ids  = set(_routes_for_term(origin).values_list('id', flat=True))
        dest_ids    = set(_routes_for_term(destination).values_list('id', flat=True))
        matched_ids = origin_ids & dest_ids

        # Ensure origin stage comes before destination stage on the route
        origin_frags = _resolve_aliases(origin)
        valid_ids = []
        for route_id in matched_ids:
            origin_q = db_models.Q()
            for frag in origin_frags:
                origin_q |= db_models.Q(name__icontains=frag)
            origin_stage = Stage.objects.filter(origin_q, route_id=route_id).order_by('order').first()
            dest_stage   = Stage.objects.filter(route_id=route_id, name__icontains=destination).order_by('order').first()
            if origin_stage and dest_stage and origin_stage.order <= dest_stage.order:
                valid_ids.append(route_id)
            elif origin_stage and not dest_stage:
                valid_ids.append(route_id)

        results = Route.objects.filter(id__in=valid_ids)

    elif origin:
        results = _routes_for_term(origin)

    elif destination:
        results = _routes_for_term(destination)

    elif query:
        results = _routes_for_term(query)

    return render(request, 'transit/home.html', {
        'results':     results,
        'origin':      origin,
        'destination': destination,
        'query':       query,
        'cbd_hubs':    cbd_hubs,
        'all_routes':  Route.objects.all(),
    })


def route_detail(request, pk):
    route = get_object_or_404(Route, pk=pk)
    stages = route.stages.all()
    return render(request, 'transit/route_detail.html', {'route': route, 'stages': stages})


def explore(request):
    routes = Route.objects.prefetch_related('stages').all()
    # Build a list of all stages with route info for the map
    stages = Stage.objects.select_related('route').all()
    return render(request, 'transit/explore.html', {'routes': routes, 'stages': stages})


def contribute(request):
    routes = Route.objects.all()
    if request.method == 'POST':
        Contribution.objects.create(
            name=request.POST.get('name', '').strip(),
            route_id=request.POST.get('route') or None,
            type=request.POST.get('type'),
            content=request.POST.get('content', '').strip(),
        )
        messages.success(request, 'Thanks! Your contribution has been submitted for review.')
        return redirect('contribute')
    return render(request, 'transit/contribute.html', {'routes': routes})
