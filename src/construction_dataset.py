"""Construction du dataset de maintenance predictive a partir des donnees Binsa.

Principe : pour un couple (fenetre d'observation -> fenetre de prediction), on produit
une ligne par ascenseur avec ses variables explicatives et ses deux etiquettes.
La fonction `folds_glissants` empile plusieurs couples pour multiplier les exemples.
"""
import pandas as pd

# Origines considerees comme de vraies defaillances materielles de l'appareil
CAUSES_MATERIELLES = {
    "En defaut", "En défaut", "Defaillance materiel", "Défaillance matériel",
    "Materiel vetuste", "Matériel vétuste", "dereglage/desserage",
    "déréglage/desserage", "Bruit",
}


def variables_observation(g):
    """Calcule les variables explicatives d'un ascenseur sur la fenetre d'observation."""
    dep = g[g["TypeRapport"] == "Intervention"]
    return pd.Series({
        "nb_interv_total":    len(g),
        "nb_depannages":      len(dep),
        "nb_maintenances":    (g["TypeRapport"] == "Maintenance").sum(),
        "nb_anomalies":       (g["Anomalie"] == "Anomalie").sum(),
        "nb_defaillance_mat": dep["Origine"].isin(CAUSES_MATERIELLES).sum(),
        "nb_en_defaut":       dep["Origine"].isin({"En defaut", "En défaut"}).sum(),
        "nb_vetuste":         dep["Origine"].isin({"Materiel vetuste", "Matériel vétuste"}).sum(),
    })


def construire_fold(hist, parc_asc, asc_refs, obs_start, obs_end, pred_start, pred_end):
    """Construit un jeu de donnees (1 ligne / ascenseur) pour un couple de fenetres."""
    obs = hist[(hist["Date_dt"] >= obs_start) & (hist["Date_dt"] < obs_end)
               & (hist["Référence"].isin(asc_refs))]
    pred = hist[(hist["Date_dt"] >= pred_start) & (hist["Date_dt"] < pred_end)
                & (hist["Référence"].isin(asc_refs))]
    F = obs.groupby("Référence").apply(variables_observation, include_groups=False)
    dep = pred[pred["TypeRapport"] == "Intervention"]
    ta = set(dep["Référence"])
    tm = set(dep[dep["Origine"].isin(CAUSES_MATERIELLES)]["Référence"])
    ds = parc_asc.join(F).fillna({c: 0 for c in F.columns})
    ds["age"] = (pred_start.year
                 - pd.to_datetime(ds["Date de debut de contrat"], errors="coerce").dt.year).clip(lower=0)
    ds["target_all"] = ds.index.isin(ta).astype(int)
    ds["target_mat"] = ds.index.isin(tm).astype(int)
    ds["origine_obs"] = obs_start.date().isoformat()
    return ds


def folds_glissants(hist, parc_asc, asc_refs, origines, obs_mois=9, pred_mois=3):
    """Empile plusieurs folds en faisant glisser les fenetres dans le temps.

    `origines` : liste de dates de debut de la fenetre d'observation (pd.Timestamp).
    Chaque origine produit un fold ; on les concatene pour l'entrainement.
    """
    dfs = []
    for o in origines:
        obs_end = o + pd.DateOffset(months=obs_mois)
        pred_end = obs_end + pd.DateOffset(months=pred_mois)
        dfs.append(construire_fold(hist, parc_asc, asc_refs, o, obs_end, obs_end, pred_end))
    return pd.concat(dfs)
