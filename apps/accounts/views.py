from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.urls import reverse
from .forms import (
    UserRegistrationForm, 
    UserProfileForm, 
    CustomAuthenticationForm,
    UserUpdateForm
)
from .models import User
from django.db.models import Count, Q

def login_view(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
                
                # Redirect based on role
                next_url = request.GET.get('next', 'core:dashboard')
                return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'accounts/login.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('accounts:login')

@login_required
def profile_view(request):
    user = request.user
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(instance=user)
    
    context = {
        'form': form,
        'user': user,
    }
    
    return render(request, 'accounts/profile.html', context)

@login_required
def change_password_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect('accounts:profile')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'accounts/change_password.html', {'form': form})

@login_required
def user_list_view(request):
    if not request.user.is_admin and not request.user.is_fsm:
        messages.error(request, 'You do not have permission to view users.')
        return redirect('core:dashboard')
    
    users = User.objects.all().order_by('-date_joined')
    
    # Filter by role if specified
    role_filter = request.GET.get('role', '')
    if role_filter:
        users = users.filter(role=role_filter)
    
    # Search by name or username
    search_query = request.GET.get('search', '')
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    context = {
        'users': users,
        'role_filter': role_filter,
        'search_query': search_query,
        'role_choices': User.ROLE_CHOICES,
    }
    
    return render(request, 'accounts/user_list.html', context)

@login_required
def user_create_view(request):
    if not request.user.is_admin:
        messages.error(request, 'Only administrators can create users.')
        return redirect('accounts:user_list')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'User {user.username} created successfully!')
            return redirect('accounts:user_list')
    else:
        form = UserRegistrationForm()
    
    context = {
        'form': form,
        'title': 'Create New User',
    }
    
    return render(request, 'accounts/user_form.html', context)

@login_required
def user_update_view(request, pk):
    if not request.user.is_admin:
        messages.error(request, 'Only administrators can edit users.')
        return redirect('accounts:user_list')
    
    user = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, f'User {user.username} updated successfully!')
            return redirect('accounts:user_list')
    else:
        form = UserUpdateForm(instance=user)
    
    context = {
        'form': form,
        'title': f'Edit User: {user.username}',
        'user': user,
    }
    
    return render(request, 'accounts/user_form.html', context)

@login_required
def user_detail_view(request, pk):
    if not request.user.is_admin and not request.user.is_fsm:
        messages.error(request, 'You do not have permission to view user details.')
        return redirect('core:dashboard')
    
    user = get_object_or_404(User, pk=pk)
    
    # Get user activity stats
    from apps.hiring.models import Quotation, HireOrder
    from apps.finance.models import Invoice
    
    quotations = Quotation.objects.filter(prepared_by=user).count()
    orders = HireOrder.objects.filter(created_by=user).count()
    invoices = Invoice.objects.filter(issued_by=user).count()
    
    context = {
        'user_detail': user,
        'quotations_count': quotations,
        'orders_count': orders,
        'invoices_count': invoices,
    }
    
    return render(request, 'accounts/user_detail.html', context)

@login_required
def user_toggle_active(request, pk):
    if not request.user.is_admin:
        messages.error(request, 'Only administrators can change user status.')
        return redirect('accounts:user_list')
    
    user = get_object_or_404(User, pk=pk)
    user.is_active = not user.is_active
    user.save()
    
    status = 'activated' if user.is_active else 'deactivated'
    messages.success(request, f'User {user.username} has been {status}.')
    
    return redirect('accounts:user_list')