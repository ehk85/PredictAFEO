"""Genere l'interpretation du score. Un histogramme mensuel du risque de panne
+ un court texte de lecture. Utilise les references sauvegardees dans le modele.
"""
import io
import base64
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

MOIS_LABELS = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Août", "Sep", "Oct", "Nov", "Déc"]

# Bornes fixes (0 -> 50 %) pour que le degrade de couleur ait la meme echelle
# d'un appareil a l'autre. Un mois n'est rouge que s'il depasse un risque reel eleve.
_CMAP = matplotlib.colormaps["RdYlGn_r"]
_VMAX = 0.5


def generer_graphique_mensuel(proba, saisonnalite):
    """Combine le score individuel de l'appareil avec la saisonnalite historique
    des defaillances materielles du parc pour produire un profil mensuel de risque,
    puis le rend sous forme d'histogramme"""
    idx = saisonnalite or {}
    valeurs = [min(0.95, max(0.01, proba * idx.get(m, 1.0))) for m in range(1, 13)]
    couleurs = [_CMAP(min(v, _VMAX) / _VMAX) for v in valeurs]

    fig, ax = plt.subplots(figsize=(8, 3.6))
    barres = ax.bar(MOIS_LABELS, [v * 100 for v in valeurs], color=couleurs, edgecolor="white", linewidth=0.6)
    ax.set_ylabel("Risque de panne estimé (%)")
    ax.set_title("Tendance mensuelle du risque de panne")
    ax.set_ylim(0, max(55, max(valeurs) * 100 * 1.15))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for b, v in zip(barres, valeurs):
        ax.annotate(f"{v * 100:.0f}%", (b.get_x() + b.get_width() / 2, b.get_height()),
                    ha="center", va="bottom", fontsize=8)
    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def interpreter(vals, proba, bundle):
    ref = bundle.get("ref", {})
    scores = np.array(ref.get("scores_tries", []))

    # rang dans le parc 
    if len(scores):
        top = 100 - 100 * (scores < proba).mean()       # position depuis le haut du parc
    else:
        top = 100

    if top <= 15:
        niveau, action = "ÉLEVÉ", "À inspecter en priorité ce trimestre : il figure parmi les appareils les plus à risque du parc."
    elif top <= 40:
        niveau, action = "MODÉRÉ", "À surveiller de près : il se situe dans la moitié haute du parc en matière de risque."
    else:
        niveau, action = "FAIBLE", "Aucune action prioritaire : suivi normal."

    graphique = generer_graphique_mensuel(proba, ref.get("saisonnalite_mois"))
    legende = ("Chaque barre combine le score de risque de cet appareil avec la "
               "saisonnalité historique des pannes du parc. Plus la couleur tire vers le rouge, "
               "plus le mois est à risque.")

    return {
        "niveau": niveau, "proba": round(100 * proba, 1), "action": action,
        "graphique": graphique, "legende": legende,
    }
