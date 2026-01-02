from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    # Dashboard
    path('', views.DocumentDashboardView.as_view(), name='dashboard'),
    
    # Document management
    path('documents/', views.DocumentListView.as_view(), name='document_list'),
    path('documents/<int:pk>/', views.DocumentDetailView.as_view(), name='document_detail'),
    path('documents/<int:pk>/download/', views.DocumentDownloadView.as_view(), name='document_download'),
    path('documents/<int:pk>/preview/', views.DocumentPreviewView.as_view(), name='document_preview'),
    path('documents/<int:pk>/send/', views.DocumentSendView.as_view(), name='document_send'),
    path('documents/<int:pk>/archive/', views.DocumentArchiveView.as_view(), name='document_archive'),
    path('documents/<int:pk>/delete/', views.delete_document, name='document_delete'),
    
    # Document generation
    path('generate/<str:doc_type>/<int:object_id>/', views.GenerateDocumentView.as_view(), name='generate_document'),
    
    # Template management
    path('templates/', views.TemplateListView.as_view(), name='template_list'),
    path('templates/create/', views.TemplateCreateView.as_view(), name='template_create'),
    path('templates/<int:pk>/edit/', views.TemplateUpdateView.as_view(), name='template_edit'),
    path('templates/<int:pk>/preview/', views.TemplatePreviewView.as_view(), name='template_preview'),
    
    # Settings
    path('settings/', views.DocumentSettingsView.as_view(), name='settings'),
    
    # Bulk actions
    path('bulk-action/', views.BulkDocumentActionView.as_view(), name='bulk_action'),
    
    # Statistics and reports
    path('stats/', views.DocumentStatsView.as_view(), name='stats'),
    
    # API endpoints
    path('api/counts/', views.GetDocumentCountsView.as_view(), name='api_counts'),
    path('api/recent/', views.GetRecentDocumentsView.as_view(), name='api_recent'),
]