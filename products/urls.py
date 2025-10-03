# products/urls.py

from django.urls import path
# Remove a importação da ProductListView
from .views import StandardizeProductView, IncrementProductScoreView, ProductParseView

urlpatterns = [
    path('parse/', ProductParseView.as_view(), name='parse-product'),
    # A rota de busca agora também lida com a listagem
    path('standardize/', StandardizeProductView.as_view(), name='standardize-product'),
    
    path('<slug:product_id>/increment_score/', IncrementProductScoreView.as_view(), name='increment-score'),
]