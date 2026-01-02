from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def dashboard(request):
    context = {
        'page_title': 'Dashboard',
    }
    
    # Role-specific context
    if request.user.is_fsm or request.user.is_admin:
        # FSM/Admin dashboard
        return render(request, 'core/dashboard_fsm.html', context)
    elif request.user.is_hce:
        # HCE dashboard
        return render(request, 'core/dashboard_hce.html', context)
    elif request.user.is_scaffolder():
        # Scaffolder dashboard
        return render(request, 'core/dashboard_scaffolder.html', context)
    else:
        # Default dashboard
        return render(request, 'core/dashboard.html', context)