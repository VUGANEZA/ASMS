from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def rema_staff_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.role not in ['rema_officer', 'rema_admin']:
            messages.error(request, "You do not have permission to access the REMA officer area.")
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper