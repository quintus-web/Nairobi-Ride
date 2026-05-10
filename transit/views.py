from django.shortcuts import render, get_object_or_404
from .models import Route


def home(request):
    query = request.GET.get('q', '').strip()
    results = None
    if query:
        results = Route.objects.filter(number__icontains=query) | Route.objects.filter(destination__icontains=query)
    return render(request, 'transit/home.html', {
        'results': results,
        'query': query,
        'all_routes': Route.objects.all(),
    })


def route_detail(request, pk):
    route = get_object_or_404(Route, pk=pk)
    stages = route.stages.all()
    return render(request, 'transit/route_detail.html', {'route': route, 'stages': stages})
