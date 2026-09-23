"""Point d'entree Vercel : expose l'application Flask existante (application/app.py)
sans dupliquer son code. Vercel importe l'objet WSGI `app` depuis ce fichier.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from application.app import app  # noqa: E402
