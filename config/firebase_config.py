import firebase_admin
from firebase_admin  import credentials, firestore
import os
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

cred_path = os.path.join(BASE_DIR, 'firebase-credentials.json')

try:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)

    db = firestore.client()

    print(">>> Conexão com o Firebase inicializada com sucesso! <<<")

except Exception as e:
    print(f">>> ERRO ao inicializar o Firebase: {e} <<<")
    db = None