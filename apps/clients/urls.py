from django.urls import path
from . import views

app_name = 'clients'

urlpatterns = [
    # Dashboard
    path('', views.ClientDashboardView.as_view(), name='dashboard'),
    
    # Client management
    path('clients/', views.ClientListView.as_view(), name='client_list'),
    path('clients/create/', views.ClientCreateView.as_view(), name='client_create'),
    path('clients/<int:pk>/', views.ClientDetailView.as_view(), name='client_detail'),
    path('clients/<int:pk>/edit/', views.ClientUpdateView.as_view(), name='client_edit'),
    path('clients/<int:pk>/delete/', views.ClientDeleteView.as_view(), name='client_delete'),
    path('clients/<int:pk>/verify/', views.MarkClientVerifiedView.as_view(), name='client_verify'),
    path('clients/<int:pk>/update-balance/', views.UpdateClientBalanceView.as_view(), name='update_balance'),
    
    # Notes and communications
    path('clients/<int:pk>/add-note/', views.AddClientNoteView.as_view(), name='add_note'),
    path('clients/<int:pk>/add-contact/', views.AddClientContactView.as_view(), name='add_contact'),
    path('clients/<int:pk>/add-site/', views.AddClientSiteView.as_view(), name='add_site'),
    path('clients/<int:pk>/add-document/', views.AddClientDocumentView.as_view(), name='add_document'),
    
    # Credit notes
    path('clients/<int:pk>/credit-notes/', views.ClientCreditNotesView.as_view(), name='client_credit_notes'),
    path('clients/<int:pk>/credit-notes/create/', views.CreateCreditNoteView.as_view(), name='create_credit_note'),
    path('credit-notes/<int:pk>/apply/', views.ApplyCreditNoteView.as_view(), name='apply_credit_note'),
    
    # Ratings
    path('clients/<int:pk>/ratings/', views.ClientRatingsView.as_view(), name='client_ratings'),
    path('clients/<int:pk>/ratings/add/', views.AddClientRatingView.as_view(), name='add_rating'),
    
    # Blacklist
    path('clients/<int:pk>/blacklist/', views.BlacklistClientView.as_view(), name='blacklist_client'),
    path('clients/<int:pk>/remove-blacklist/', views.RemoveFromBlacklistView.as_view(), name='remove_blacklist'),
    
    # Reports
    path('reports/', views.ClientReportsView.as_view(), name='reports'),
    path('export/', views.ClientExportView.as_view(), name='export'),
    
    # API endpoints
    path('api/autocomplete/', views.ClientAutocompleteView.as_view(), name='api_autocomplete'),
    path('api/stats/', views.ClientStatsView.as_view(), name='api_stats'),
    path('notes/<int:pk>/resolve/', views.mark_note_resolved, name='resolve_note'),
    path('documents/<int:pk>/delete/', views.delete_document, name='delete_document'),
]