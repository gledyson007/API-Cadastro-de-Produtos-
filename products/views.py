import os
import requests
import unicodedata
import re
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from config.authentication import FirebaseAuthentication
from rest_framework.permissions import IsAuthenticated
from config.firebase_config import db
from firebase_admin import firestore



def normalize_text(text):
    if not text: return ""
    text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    text = re.sub(r'[^a-z0-9\s]', '', text.lower())
    text = re.sub(r'\s+', '-', text.strip())
    if len(text) > 50: text = text[:50]
    return text.rstrip('-')

def extract_unit_from_title(title):
    title_lower = title.lower()
    match = re.search(r'(\d+[\.,]?\d*)\s?(kg|g|ml|l)\b', title_lower)
    if match:
        unit = match.group(2)
        if unit == 'l': return 'L'
        if unit == 'ml': return 'mL'
        return unit
    return "un"

def parse_term(raw_term):
    term = raw_term.lower()
    price, unit = None, "un"
    price_match = re.search(r'(r\$|R\$)?\s?(\d+[,.]\d{2})', term)
    if price_match:
        price = float(price_match.group(2).replace(',', '.'))
        term = term.replace(price_match.group(0), '')
    unit_match = re.search(r'(\d+[\.,]?\d*)\s?(g|kg|ml|l)\b', term)
    if unit_match:
        unit = unit_match.group(2)
        if unit == 'l': unit = 'L'
        if unit == 'ml': unit = 'mL'
    name = term.strip()
    return name, price, unit

def find_best_match_in_firebase(search_keywords):
    best_match, highest_relevance = None, -1
    candidate_docs = {}
    for keyword in search_keywords:
        docs = db.collection('products').where('search_terms', 'array_contains', keyword).stream()
        for doc in docs:
            candidate_docs[doc.id] = doc.to_dict()
    if candidate_docs:
        for doc_id, doc_data in candidate_docs.items():
            doc_terms = set(doc_data.get('search_terms', []))
            relevance = len(search_keywords.intersection(doc_terms))
            popularity = doc_data.get('score', 0)
            current_best_pop = best_match.get('score', -1) if best_match else -1
            if relevance > highest_relevance or (relevance == highest_relevance and popularity > current_best_pop):
                highest_relevance = relevance
                best_match = doc_data
    return best_match

def discover_product_with_serper(name, price, unit, search_keywords):
    image_url, description = "https://placehold.co/150x150/EEE/31343C?text=Imagem\\nNao+Encontrada", None
    api_key = os.environ.get('SERPER_API_KEY')

    if not api_key: return image_url, description, unit
    headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}
    payload_images = {"q": f"{name} produto embalagem"}
    response_images = requests.post("https://google.serper.dev/images", json=payload_images, headers=headers)
    best_serper_result = response_images.json()['images'][0] if response_images.ok and response_images.json().get('images') else None
    payload_search = {"q": name}
    response_search = requests.post("https://google.serper.dev/search", json=payload_search, headers=headers)

    if response_search.ok and response_search.json().get('organic'):
        snippet = response_search.json()['organic'][0].get('snippet')
        if snippet: description = snippet[:250] + '...' if len(snippet) > 250 else snippet
        
    if best_serper_result:
        image_url = best_serper_result.get('imageUrl', image_url)
        if unit == 'un': unit = extract_unit_from_title(best_serper_result.get('title', ''))
        product_id = normalize_text(name)
        if product_id:
            product_ref = db.collection('products').document(product_id)
            if not product_ref.get().exists:
                db_data_to_save = { "name": name, "price": price, "image_url": image_url, "description": description, "source": best_serper_result.get('domain'), "unit": unit, "score": 0, "is_human_reviewed": False, "search_terms": list(search_keywords) }
                product_ref.set(db_data_to_save)
    return image_url, description, unit

def process_single_term(raw_term):
    try:
        name, price, unit = parse_term(raw_term)
        search_keywords = set([kw for kw in normalize_text(name).replace('-', ' ').split() if len(kw) > 2])
        best_match = find_best_match_in_firebase(search_keywords)
        if best_match:
            image_url, description = best_match.get('image_url'), best_match.get('description')
            if unit == 'un': unit = best_match.get('unit', 'un')
        else:
            image_url, description, unit = discover_product_with_serper(name, price, unit, search_keywords)
        return { "name": name, "price": price, "unitOfMeasure": unit, "imageUrl": image_url, "description": description }
    except Exception as e:
        return {"error": f"Não foi possível processar o termo: {raw_term}", "details": str(e)}


class ProductParseView(APIView):
    authentication_classes = [FirebaseAuthentication]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        terms_list = request.data.get('terms')
        if not isinstance(terms_list, list):
            return Response({"error": "O corpo da requisição deve conter uma lista no campo 'terms'."}, status=status.HTTP_400_BAD_REQUEST)
        response_data = [process_single_term(term) for term in terms_list]
        return Response(response_data, status=status.HTTP_200_OK)

class StandardizeProductView(APIView):
    authentication_classes = [FirebaseAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self, request):
        if db is None:
            return Response({"error": "A conexão com o Firebase falhou."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        query = request.query_params.get('q')
        if query and query.strip():
            try:
                normalized_search_term = normalize_text(query).replace('-', ' ')
                docs_query = db.collection('products').where('search_terms', 'array_contains', normalized_search_term)
                docs = docs_query.stream()
                firebase_results = []
                for doc in docs:
                    product_data = doc.to_dict()
                    product_data['product_id'] = doc.id
                    firebase_results.append(product_data)
                if firebase_results:
                    sorted_results = sorted(firebase_results, key=lambda p: p.get('score', 0), reverse=True)
                    return Response(sorted_results, status=status.HTTP_200_OK)
                else:
                    return Response([], status=status.HTTP_200_OK)
            except Exception as e:
                return Response({"error": f"Erro na busca: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            try:
                docs = db.collection('products').stream()
                all_products = []
                for doc in docs:
                    product_data = doc.to_dict()
                    product_data['product_id'] = doc.id
                    all_products.append(product_data)
                sorted_products = sorted(all_products, key=lambda p: p.get('score', 0), reverse=True)
                return Response(sorted_products, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({"error": f"Erro ao listar produtos: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class IncrementProductScoreView(APIView):
    authentication_classes = [FirebaseAuthentication]
    permission_classes = [IsAuthenticated]
    def post(self, request, product_id):
        if not product_id:
            return Response({"error": "ID do produto é obrigatório."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            product_ref = db.collection('products').document(product_id)
            doc = product_ref.get()
            if doc.exists:
                product_ref.update({'score': firestore.Increment(1)})
            else:
                product_data = request.data
                product_name_for_terms = normalize_text(product_data.get('name', '')).replace('-', ' ')
                search_terms = list(set([term for term in product_name_for_terms.split() if len(term) > 2]))
                db_data_to_save = {
                    "name": product_data.get('name'), "image_url": product_data.get('image_url'),
                    "source": product_data.get('source'), "unit": product_data.get('unit'),
                    "description": product_data.get('description'), "score": 1, 
                    "is_human_reviewed": False, "search_terms": search_terms
                }
                product_ref.set(db_data_to_save)
            return Response({"success": f"Pontuação para o produto '{product_id}' processada."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Erro inesperado ao processar o voto: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)