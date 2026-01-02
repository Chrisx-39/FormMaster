from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .serializers import *
from apps.inventory.models import Material
from apps.hiring.models import HireOrder, Quotation

class MaterialViewSet(viewsets.ModelViewSet):
    """API endpoint for materials"""
    queryset = Material.objects.all()
    serializer_class = MaterialSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category', 'condition', 'location']
    
    @action(detail=False, methods=['get'])
    def available(self, request):
        """Get available materials only"""
        queryset = self.get_queryset().filter(available_quantity__gt=0)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Get low stock materials"""
        queryset = self.get_queryset().filter(
            available_quantity__lte=models.F('minimum_stock_level')
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class HireOrderViewSet(viewsets.ModelViewSet):
    """API endpoint for hire orders"""
    queryset = HireOrder.objects.all()
    serializer_class = HireOrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'payment_status', 'client']
    
    @action(detail=True, methods=['post'])
    def dispatch(self, request, pk=None):
        """Mark order as dispatched"""
        order = self.get_object()
        if order.status not in ['ORDERED', 'APPROVED']:
            return Response(
                {'error': 'Order cannot be dispatched from current status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.status = 'DISPATCHED'
        order.save()
        
        # Update dispatched quantities
        for item in order.items.all():
            item.quantity_dispatched = item.quantity_ordered
            item.save()
        
        serializer = self.get_serializer(order)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def return_order(self, request, pk=None):
        """Mark order as returned"""
        order = self.get_object()
        if order.status != 'ACTIVE':
            return Response(
                {'error': 'Only active orders can be returned'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.status = 'RETURNED'
        order.actual_return_date = timezone.now().date()
        order.save()
        
        # Return inventory
        for item in order.items.all():
            material = item.material
            material.available_quantity += item.quantity_dispatched
            material.hired_quantity -= item.quantity_dispatched
            material.save()
        
        serializer = self.get_serializer(order)
        return Response(serializer.data)

class QuotationViewSet(viewsets.ModelViewSet):
    """API endpoint for quotations"""
    queryset = Quotation.objects.all()
    serializer_class = QuotationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'client']
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve quotation"""
        quotation = self.get_object()
        if quotation.status != 'DRAFT':
            return Response(
                {'error': 'Only draft quotations can be approved'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        quotation.status = 'SENT'
        quotation.approved_by = request.user
        quotation.save()
        
        serializer = self.get_serializer(quotation)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def convert_to_order(self, request, pk=None):
        """Convert quotation to order"""
        quotation = self.get_object()
        if quotation.status != 'ACCEPTED':
            return Response(
                {'error': 'Only accepted quotations can be converted to orders'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check inventory availability
        for item in quotation.items.all():
            if item.material.available_quantity < item.quantity:
                return Response(
                    {'error': f'Insufficient stock for {item.material.name}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Create order
        order = HireOrder.objects.create(
            quotation=quotation,
            client=quotation.client,
            start_date=timezone.now().date(),
            expected_return_date=timezone.now().date() + timedelta(days=quotation.hire_duration_days),
            hire_duration_days=quotation.hire_duration_days,
            created_by=request.user
        )
        
        # Create order items and reserve inventory
        for quotation_item in quotation.items.all():
            HireOrderItem.objects.create(
                hire_order=order,
                material=quotation_item.material,
                quantity_ordered=quotation_item.quantity
            )
            
            # Reserve inventory
            quotation_item.material.available_quantity -= quotation_item.quantity
            quotation_item.material.hired_quantity += quotation_item.quantity
            quotation_item.material.save()
        
        quotation.status = 'CONVERTED'
        quotation.save()
        
        serializer = HireOrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)