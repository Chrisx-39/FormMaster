from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
import json
from datetime import datetime, timedelta
from .models import Material, MaterialCategory, MaterialInspection
from .forms import (
    MaterialForm, 
    MaterialCategoryForm, 
    MaterialInspectionForm,
    MaterialAdjustmentForm
)
from apps.hiring.models import HireOrder
from apps.reporting.utils import export_to_excel

@login_required
def material_list(request):
    if not request.user.is_fsm and not request.user.is_hce and not request.user.is_admin:
        messages.error(request, 'You do not have permission to view inventory.')
        return redirect('core:dashboard')
    
    materials = Material.objects.all().order_by('category__name', 'name')
    
    # Apply filters
    category_id = request.GET.get('category', '')
    if category_id:
        materials = materials.filter(category_id=category_id)
    
    condition = request.GET.get('condition', '')
    if condition:
        materials = materials.filter(condition=condition)
    
    search_query = request.GET.get('search', '')
    if search_query:
        materials = materials.filter(
            Q(name__icontains=search_query) |
            Q(code__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(materials, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    categories = MaterialCategory.objects.all()
    
    context = {
        'materials': page_obj,
        'categories': categories,
        'category_filter': category_id,
        'condition_filter': condition,
        'search_query': search_query,
        'condition_choices': Material.CONDITION_CHOICES,
    }
    
    return render(request, 'inventory/material_list.html', context)

@login_required
def material_detail(request, pk):
    if not request.user.is_fsm and not request.user.is_hce and not request.user.is_admin:
        messages.error(request, 'You do not have permission to view material details.')
        return redirect('core:dashboard')
    
    material = get_object_or_404(Material, pk=pk)
    
    # Get hire history
    hire_history = HireOrder.objects.filter(
        items__material=material
    ).distinct().order_by('-order_date')[:10]
    
    # Get inspection history
    inspections = MaterialInspection.objects.filter(
        material=material
    ).order_by('-inspection_date')[:10]
    
    # Get utilization stats
    total_hires = HireOrder.objects.filter(items__material=material).count()
    
    context = {
        'material': material,
        'hire_history': hire_history,
        'inspections': inspections,
        'total_hires': total_hires,
    }
    
    return render(request, 'inventory/material_detail.html', context)

@login_required
def material_create(request):
    if not request.user.is_fsm and not request.user.is_admin:
        messages.error(request, 'Only FSM or Administrators can create materials.')
        return redirect('inventory:material_list')
    
    if request.method == 'POST':
        form = MaterialForm(request.POST)
        if form.is_valid():
            material = form.save()
            messages.success(request, f'Material {material.name} created successfully!')
            return redirect('inventory:material_detail', pk=material.pk)
    else:
        form = MaterialForm()
    
    context = {
        'form': form,
        'title': 'Create New Material',
    }
    
    return render(request, 'inventory/material_form.html', context)

@login_required
def material_update(request, pk):
    if not request.user.is_fsm and not request.user.is_admin:
        messages.error(request, 'Only FSM or Administrators can edit materials.')
        return redirect('inventory:material_list')
    
    material = get_object_or_404(Material, pk=pk)
    
    if request.method == 'POST':
        form = MaterialForm(request.POST, instance=material)
        if form.is_valid():
            material = form.save()
            messages.success(request, f'Material {material.name} updated successfully!')
            return redirect('inventory:material_detail', pk=material.pk)
    else:
        form = MaterialForm(instance=material)
    
    context = {
        'form': form,
        'title': f'Edit Material: {material.name}',
        'material': material,
    }
    
    return render(request, 'inventory/material_form.html', context)

@login_required
def material_delete(request, pk):
    if not request.user.is_admin:
        messages.error(request, 'Only administrators can delete materials.')
        return redirect('inventory:material_list')
    
    material = get_object_or_404(Material, pk=pk)
    
    # Check if material is in use
    if HireOrder.objects.filter(items__material=material).exists():
        messages.error(request, f'Cannot delete {material.name} because it is currently hired or has hire history.')
        return redirect('inventory:material_detail', pk=material.pk)
    
    if request.method == 'POST':
        material_name = material.name
        material.delete()
        messages.success(request, f'Material {material_name} deleted successfully!')
        return redirect('inventory:material_list')
    
    context = {
        'material': material,
    }
    
    return render(request, 'inventory/material_confirm_delete.html', context)

@login_required
def material_inspect(request, pk):
    if not request.user.is_scaffolder and not request.user.is_admin:
        messages.error(request, 'Only scaffolders can perform inspections.')
        return redirect('inventory:material_detail', pk=pk)
    
    material = get_object_or_404(Material, pk=pk)
    
    if request.method == 'POST':
        form = MaterialInspectionForm(request.POST)
        if form.is_valid():
            inspection = form.save(commit=False)
            inspection.material = material
            inspection.inspector = request.user
            
            # Update material condition
            material.condition = inspection.condition
            material.last_inspection_date = inspection.inspection_date.date()
            material.save()
            
            inspection.save()
            
            messages.success(request, f'Inspection completed for {material.name}.')
            return redirect('inventory:material_detail', pk=material.pk)
    else:
        form = MaterialInspectionForm(initial={
            'material': material,
            'inspector': request.user,
            'next_inspection_date': datetime.now().date() + timedelta(days=30)
        })
    
    context = {
        'form': form,
        'material': material,
        'title': f'Inspect Material: {material.name}',
    }
    
    return render(request, 'inventory/material_inspect.html', context)

@login_required
def material_adjust_stock(request, pk):
    if not request.user.is_fsm and not request.user.is_admin:
        messages.error(request, 'Only FSM or Administrators can adjust stock.')
        return redirect('inventory:material_detail', pk=pk)
    
    material = get_object_or_404(Material, pk=pk)
    
    if request.method == 'POST':
        form = MaterialAdjustmentForm(request.POST)
        if form.is_valid():
            adjustment_type = form.cleaned_data['adjustment_type']
            quantity = form.cleaned_data['quantity']
            reason = form.cleaned_data['reason']
            
            if adjustment_type == 'ADD':
                material.total_quantity += quantity
                material.available_quantity += quantity
                adjustment_desc = f'Added {quantity} units'
            else:  # REMOVE
                if material.available_quantity < quantity:
                    messages.error(request, f'Cannot remove {quantity} units. Only {material.available_quantity} available.')
                    return redirect('inventory:material_adjust_stock', pk=material.pk)
                
                material.total_quantity -= quantity
                material.available_quantity -= quantity
                adjustment_desc = f'Removed {quantity} units'
            
            material.save()
            
            # Log the adjustment
            from django.contrib.admin.models import LogEntry, CHANGE
            from django.contrib.contenttypes.models import ContentType
            
            LogEntry.objects.log_action(
                user_id=request.user.id,
                content_type_id=ContentType.objects.get_for_model(material).pk,
                object_id=material.id,
                object_repr=str(material),
                action_flag=CHANGE,
                change_message=f'{adjustment_desc}. Reason: {reason}'
            )
            
            messages.success(request, f'Stock adjusted: {adjustment_desc.lower()}.')
            return redirect('inventory:material_detail', pk=material.pk)
    else:
        form = MaterialAdjustmentForm()
    
    context = {
        'form': form,
        'material': material,
        'title': f'Adjust Stock: {material.name}',
    }
    
    return render(request, 'inventory/material_adjust_stock.html', context)

@login_required
def inventory_dashboard(request):
    if not request.user.is_fsm and not request.user.is_admin:
        messages.error(request, 'You do not have permission to view inventory dashboard.')
        return redirect('core:dashboard')
    
    # Get statistics
    total_materials = Material.objects.count()
    low_stock_materials = Material.objects.filter(
        available_quantity__lte=models.F('minimum_stock_level')
    ).count()
    
    # Materials by category
    materials_by_category = Material.objects.values(
        'category__name'
    ).annotate(
        total=Count('id'),
        available=Sum('available_quantity'),
        hired=Sum('hired_quantity')
    ).order_by('category__name')
    
    # Low stock items
    low_stock_items = Material.objects.filter(
        available_quantity__lte=models.F('minimum_stock_level')
    ).order_by('available_quantity')[:10]
    
    # Materials needing inspection (last inspection > 30 days ago)
    thirty_days_ago = datetime.now().date() - timedelta(days=30)
    needs_inspection = Material.objects.filter(
        Q(last_inspection_date__isnull=True) |
        Q(last_inspection_date__lt=thirty_days_ago)
    ).count()
    
    # Top materials by utilization
    top_materials = Material.objects.annotate(
        utilization=100.0 * models.F('hired_quantity') / models.F('total_quantity')
    ).order_by('-utilization')[:10]
    
    context = {
        'total_materials': total_materials,
        'low_stock_materials': low_stock_materials,
        'materials_by_category': materials_by_category,
        'low_stock_items': low_stock_items,
        'needs_inspection': needs_inspection,
        'top_materials': top_materials,
    }
    
    return render(request, 'inventory/dashboard.html', context)

@login_required
def check_availability(request):
    """AJAX endpoint to check material availability"""
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            data = json.loads(request.body)
            material_id = data.get('material_id')
            quantity_needed = int(data.get('quantity', 0))
            
            material = get_object_or_404(Material, pk=material_id)
            
            available = material.available_quantity >= quantity_needed
            
            return JsonResponse({
                'available': available,
                'available_quantity': material.available_quantity,
                'material_name': material.name,
                'message': f'Available: {material.available_quantity} units' if available else f'Only {material.available_quantity} units available'
            })
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({'error': 'Invalid request'}, status=400)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@login_required
def export_inventory(request):
    if not request.user.is_fsm and not request.user.is_admin:
        messages.error(request, 'You do not have permission to export inventory.')
        return redirect('inventory:material_list')
    
    materials = Material.objects.all().order_by('category__name', 'name')
    
    # Prepare data for export
    data = []
    for material in materials:
        data.append({
            'Code': material.code,
            'Name': material.name,
            'Category': material.category.name,
            'Unit': material.unit_of_measure,
            'Total Quantity': material.total_quantity,
            'Available': material.available_quantity,
            'Hired': material.hired_quantity,
            'Daily Rate': f"${material.daily_hire_rate}",
            'Condition': material.get_condition_display(),
            'Location': material.location,
            'Min Stock': material.minimum_stock_level,
            'Last Inspection': material.last_inspection_date,
        })
    
    # Export to Excel
    filename = f'inventory_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    response = export_to_excel(data, filename, 'Inventory Report')
    
    return response