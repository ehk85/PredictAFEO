# Maintenance prédictive des ascenseurs — AFEO (projet Nexa Digital School)

Preuve de concept d'un modèle d'apprentissage supervisé estimant le risque de panne
trimestriel d'un ascenseur à partir du seul historique d'interventions (données Binsa),
avec une application web de scoring.

## Résultat principal

En validation temporelle (entraînement sur 2025, test sur un trimestre 2026 jamais vu),
la forêt aléatoire atteint une **AUC de 0,79** sur la cible « défaillance matérielle »,
portée à **0,81** après enrichissement (fiche technique + NLP des commentaires).

---

## 1. Prérequis d'installation

- Python 3.10 ou supérieur
- Les dépendances listées dans `requirements.txt` (nécessaires pour faire tourner l'application)
  et, pour réentraîner le modèle ou utiliser le notebook, celles de `requirements-dev.txt`
- (Optionnel) un outil pour ouvrir une base SQLite (DB Browser for SQLite, ou la lib `sqlite3` incluse dans Python)

## 2. Étapes d'installation

```bash
# 1. Se placer dans le dossier du projet
cd memoire_maintenance_predictive_ascenseurs

# 2. (Recommandé) créer un environnement virtuel
python -m venv venv
source venv/bin/activate        # Windows : venv\Scripts\activate

# 3. Installer les dépendances (application uniquement)
pip install -r requirements.txt
# ... ou, pour aussi pouvoir reentrainer le modele / utiliser le notebook :
pip install -r requirements-dev.txt
```

## 3. Lancer l'analyse et (ré)entraîner le modèle

Nécessite `requirements-dev.txt` et les exports Binsa dans `donnees/` (non fournis dans ce
dépôt pour des raisons de confidentialité — voir section 6).

```bash
python src/analyse_principale.py          # modélisation + figures + métriques
python src/enrichissement_fiche_technique.py
python src/enrichissement_nlp_recence.py
python application/entrainer_modele.py    # entraîne et sauvegarde le modèle de l'appli
```

## 4. Lancer l'application web

```bash
python application/app.py
```
Puis ouvrir **http://127.0.0.1:5001** dans un navigateur.

- **Compatibilité multi-navigateur** : interface testée sur Chrome, Firefox et Edge (HTML/CSS standard, sans dépendance propriétaire).
- **Identifiants de test (back-office / démonstration)** : identifiant `admin` — mot de passe `afeo2026`.
  (Authentification de démonstration ; à remplacer par une gestion sécurisée en production.)

## 5. Base de données SQL

La base est fournie sous deux formes dans `base_sql/` :
- `afeo.db` : base **SQLite** prête à l'emploi (4 tables : appareils, interventions, fiche_technique, pannes_repetitives).
- `afeo_dump.sql` : **dump SQL** rejouable pour recréer la base.

Recréer la base depuis le dump :

```bash
sqlite3 nouvelle_base.db < base_sql/afeo_dump.sql
```

- **Connexion à la base** : SQLite est un fichier local, sans serveur ni identifiant réseau.
  Chemin par défaut : `base_sql/afeo.db`. (Aucun identifiant requis pour SQLite.)

> `donnees/` et `base_sql/*.db`/`*.sql` contiennent des données réelles d'AFEO et ne sont **pas
> versionnés** dans ce dépôt Git (voir `.gitignore`), par confidentialité. L'application n'en a
> pas besoin pour fonctionner (le modèle entraîné est inclus) ; ils ne sont utiles que pour
> réentraîner le modèle (section 3).

## 6. Déploiement

Le dépôt contient la configuration pour deux hébergeurs :

**Vercel** (serverless) — via `vercel.json` + `api/index.py` :

```bash
npx vercel login      # authentification (une fois)
npx vercel --prod     # déploiement
```

⚠️ Cette application embarque scikit-learn, pandas, matplotlib et un modèle de 53 Mo : c'est
lourd pour un environnement serverless. Sur l'offre gratuite de Vercel, le déploiement peut
échouer si la taille totale des dépendances dépasse la limite autorisée. Si c'est le cas,
utiliser Render (ci-dessous), plus adapté à ce type d'application.

**Render** (serveur persistant, plus adapté ici) — via `render.yaml` :
1. Créer un compte sur [render.com](https://render.com) et connecter le dépôt GitHub.
2. « New + » → « Blueprint » → sélectionner ce dépôt (`render.yaml` est détecté automatiquement).
3. Render installe `requirements.txt` et lance `gunicorn application.app:app`.

---

## Arborescence

```
.
├── README.md                     ← ce fichier
├── requirements.txt               ← dépendances de l'application (déploiement)
├── requirements-dev.txt           ← + dépendances pour réentraîner / notebook
├── vercel.json, api/index.py      ← config déploiement Vercel
├── render.yaml                    ← config déploiement Render
├── donnees/                      ← exports Binsa (non versionné, confidentiel — voir section 5)
├── base_sql/                     ← base SQLite (non versionné, confidentiel — voir section 5)
├── application/                  ← application Flask (front + back)
│   ├── app.py                    ← serveur Flask
│   ├── entrainer_modele.py       ← entraîne et sauvegarde le modèle
│   ├── modele_afeo.joblib        ← modèle sérialisé
│   ├── static/style.css          ← feuille de style
│   └── templates/                ← interface (formulaire accessible + connexion)
├── notebooks/
│   └── maintenance_predictive_ascenseurs.ipynb
├── src/                          ← code source de l'analyse
│   ├── lire_binsa.py
│   ├── construction_dataset.py
│   ├── analyse_principale.py
│   ├── enrichissement_fiche_technique.py
│   └── enrichissement_nlp_recence.py
├── resultats/                    ← figures, métriques, notes de synthèse
└── redaction/
    ├── Soutenance_AFEO.docx      ← DOCUMENT DE SOUTENANCE COMPLET (structure i → ix)
    ├── Introduction_et_problematique.docx
    ├── Partie_1_Contexte_etat_de_l_art.docx
    ├── Partie_2_Audit_des_donnees.docx
    ├── Partie_3_Methodologie.docx
    ├── Partie_4_Resultats.docx
    ├── Partie_5_Valeur_metier.docx
    ├── Conclusion.docx
    └── Journal_de_bord_donnees.md
```

## À compléter par l'étudiant (éléments hors périmètre technique)

- URL publique de l'application déployée et URL du dépôt Git (facultatif)
- Éléments d'entreprise (histoire, valeurs), budget, concurrents locaux réels
- Références bibliographiques précises (sources < 5 ans)
- Pages liminaires : page de garde finalisée, logo Nexa, remerciements, résumé
