import os
import time
from django.core.management.base import BaseCommand
from pathlib import Path
import requests
import re
import unicodedata

from config.firebase_config import db

# ==============================================================================
# --- FUNÇÕES AUXILIARES ---
# (Copiadas aqui para que o script seja autônomo e não dependa das views)
# ==============================================================================

def normalize_text(text):
    if not text: return ""
    text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    text = re.sub(r'[^a-z0-9\s]', '', text.lower())
    text = re.sub(r'\s+', '-', text.strip())
    if len(text) > 50: text = text[:50]
    text = text.rstrip('-')
    return text

def extract_unit_from_title(title):
    title_lower = title.lower()
    match = re.search(r'(\d+[\.,]?\d*)\s?(kg|g|ml|l)\b', title_lower)
    if match:
        unit = match.group(2)
        if unit == 'l': return 'L'
        if unit == 'ml': return 'mL'
        return unit
    return "un"

# ==============================================================================
# --- CLASSE DO COMANDO ---
# ==============================================================================

class Command(BaseCommand):
    help = 'Lê uma lista de produtos, busca na Serper por imagem E DESCRIÇÃO, e popula o Firestore com dados e IDs corretos.'

    API_KEY = os.environ.get('SERPER_API_KEY')
    IMAGES_API_URL = "https://google.serper.dev/images"
    SEARCH_API_URL = "https://google.serper.dev/search"
    HEADERS = {'X-API-KEY': API_KEY, 'Content-Type': 'application/json'}

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('--- Iniciando a população do banco de dados Firebase ---'))

        # --- 1. LER E LIMPAR A LISTA DE PRODUTOS ---
        try:
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            file_path = project_root / 'produtos.txt'
            
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_products = f.readlines()
                unique_products = sorted(list(set([p.strip().lower() for p in raw_products if p.strip()])))
            
            self.stdout.write(f'Encontrados {len(unique_products)} produtos únicos para processar.')
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR('Arquivo "produtos.txt" não encontrado na raiz do projeto.'))
            return

        # --- 2. PROCESSAR CADA PRODUTO DA LISTA ---
        for product_name_query in unique_products:
            self.stdout.write(f'-> Processando termo da lista: "{product_name_query}"...')
            
            try:
                # --- CHAMADA 1: BUSCAR IMAGEM ---
                payload_images = {"q": f"{product_name_query} produto embalagem"}
                response_images = requests.post(self.IMAGES_API_URL, json=payload_images, headers=self.HEADERS)
                response_images.raise_for_status()
                data_images = response_images.json()

                if not data_images.get('images'):
                    self.stderr.write(self.style.ERROR(f'    Nenhuma imagem encontrada para "{product_name_query}".'))
                    continue

                first_image = data_images['images'][0]
                raw_title = first_image.get('title', product_name_query)
                cleaned_name = raw_title.split(' - ')[0].split('|')[0].strip()

                # Gera o ID a partir do nome limpo encontrado, não da query
                product_id = normalize_text(cleaned_name)

                if not product_id:
                    self.stderr.write(self.style.ERROR(f'    Não foi possível gerar um ID válido para "{cleaned_name}".'))
                    continue
                
                # E só agora verificamos se ele já existe no banco
                product_ref = db.collection('products').document(product_id)
                if product_ref.get().exists:
                    self.stdout.write(self.style.WARNING(f'    Produto "{product_id}" já existe. Pulando.'))
                    continue

                # --- CHAMADA 2: BUSCAR DESCRIÇÃO ---
                description = None
                payload_search = {"q": product_name_query}
                response_search = requests.post(self.SEARCH_API_URL, json=payload_search, headers=self.HEADERS)
                if response_search.ok and response_search.json().get('organic'):
                    snippet = response_search.json()['organic'][0].get('snippet')
                    if snippet:
                        description = snippet[:250] + '...' if len(snippet) > 250 else snippet

                # --- 3. MONTAR O DOCUMENTO COMPLETO PARA SALVAR ---
                search_terms_text = normalize_text(cleaned_name).replace('-', ' ')
                search_terms = list(set([term for term in search_terms_text.split() if len(term) > 2]))
                
                original_terms = [term for term in normalize_text(product_name_query).replace('-', ' ').split() if len(term) > 2]
                search_terms.extend(original_terms)
                search_terms = list(set(search_terms))

                product_data = {
                    "name": cleaned_name,
                    "image_url": first_image.get('imageUrl'),
                    "description": description,
                    "source": first_image.get('domain'),
                    "unit": extract_unit_from_title(raw_title),
                    "score": 0,
                    "is_human_reviewed": False,
                    "search_terms": search_terms
                }
                
                # --- 4. SALVAR NO FIREBASE ---
                product_ref.set(product_data)
                self.stdout.write(self.style.SUCCESS(f'    Produto "{product_id}" salvo com sucesso!'))
                time.sleep(1.5) # Pausa educada para não sobrecarregar a API da Serper

            except Exception as e:
                self.stderr.write(self.style.ERROR(f'    Falha ao processar "{product_name_query}": {e}'))

        self.stdout.write(self.style.SUCCESS('--- População do banco de dados concluída! ---'))