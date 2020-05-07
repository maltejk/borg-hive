from django.shortcuts import render


def error404(request):
    """render error 404 page"""
    response = render(request, '404.html')
    response.status_code = 404
    return response


def error500(request):
    """render error 500 page"""
    response = render(request, '500.html')
    response.status_code = 500
    return response
