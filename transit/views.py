from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Route, Stage, Contribution


def home(request):
    origin      = request.GET.get('origin', '').strip()
    destination = request.GET.get('destination', '').strip()
    query       = request.GET.get('q', '').strip()   # legacy single-box support
    results     = None

    if origin and destination:
        # Routes whose stages contain the origin AND whose stages contain the destination
        origin_route_ids = Stage.objects.filter(
            name__icontains=origin
        ).values_list('route_id', flat=True)

        dest_route_ids = Stage.objects.filter(
            name__icontains=destination
        ).values_list('route_id', flat=True)

        # Also match destination against route.destination field
        dest_by_route = Route.objects.filter(
            destination__icontains=destination
        ).values_list('id', flat=True)

        matched_ids = set(origin_route_ids) & (set(dest_route_ids) | set(dest_by_route))
        results = Route.objects.filter(id__in=matched_ids)

    elif origin:
        # Routes that pass through the origin stage
        route_ids = Stage.objects.filter(name__icontains=origin).values_list('route_id', flat=True)
        results = Route.objects.filter(id__in=route_ids)

    elif destination:
        # Routes going to that destination (by stage name or route destination)
        route_ids = Stage.objects.filter(name__icontains=destination).values_list('route_id', flat=True)
        results = Route.objects.filter(
            id__in=route_ids
        ) | Route.objects.filter(destination__icontains=destination)

    elif query:
        results = Route.objects.filter(number__icontains=query) | Route.objects.filter(destination__icontains=query)

    return render(request, 'transit/home.html', {
        'results':     results,
        'origin':      origin,
        'destination': destination,
        'query':       query,
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
