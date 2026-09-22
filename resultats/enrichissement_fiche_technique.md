# Enrichissement par la fiche technique — synthèse des résultats

Ce document résume l'apport des variables de la fiche technique des appareils
(`donnees/Fiche_technique.xlsx`) au modèle. Résultats reproductibles via
`python src/enrichissement_fiche_technique.py`.

## 1. Jointure

La fiche technique se joint au jeu de données par la référence de l'appareil :
**1 849 des 1 855 ascenseurs** correspondent directement (99,7 %).

## 2. Réalité de la couverture (un résultat en soi)

Malgré des colonnes prometteuses, la plupart des champs techniques sont peu renseignés
dans Binsa. Sur les 1 855 ascenseurs :

| Champ | Taux renseigné | Exploitable ? |
|---|---|---|
| Nombre de niveaux | ~37 % | oui (partiel) |
| Charge | ~37 % | oui (partiel) |
| Année de mise en service (âge réel) | ~15 % (281 appareils) | oui (sous-ensemble) |
| Marque / modèle | ~24 %, et bruité | difficilement |
| Course, type de manœuvre | < 10 % | non |

> Le champ « Marque » mélange par ailleurs des marques d'ascensoristes et des marques de
> téléphone de cabine (ex. « anepbox », « memcom »), signe d'une saisie non normalisée.

Cette faible maturité des données est cohérente avec l'angle du mémoire : en PME, la
qualité et la complétude des données constituent le principal facteur limitant.

## 3. Impact sur la performance

En ajoutant les deux variables les mieux couvertes (nombre de niveaux, charge),
la performance progresse modestement mais réellement, en validation temporelle :

| Cible | AUC avant | AUC après | Δ |
|---|---|---|---|
| Tout dépannage | 0,772 | 0,789 | +0,017 |
| Défaillance matérielle | 0,790 | 0,805 | +0,015 |

## 4. Le résultat marquant : âge réel vs âge de contrat

Sur les 281 ascenseurs dont l'année de mise en service est connue, on compare le pouvoir
prédictif de l'âge réel et de l'âge de contrat (corrélation avec la survenue d'une panne) :

- âge **de contrat** ↔ panne : **0,017** (quasi nul)
- âge **réel** ↔ panne : **0,156** (environ 9× plus fort)

**Interprétation.** L'âge réel de l'appareil est un bien meilleur prédicteur que l'ancienneté
de contrat utilisée par défaut. La variable n'est pas en cause : c'est sa disponibilité (15 %)
qui limite son exploitation.

## 5. Recommandation (gouvernance des données)

Le principal levier d'amélioration n'est pas algorithmique mais organisationnel :
**instaurer la saisie systématique de la date de mise en service** (et normaliser marque/modèle)
dans Binsa. À terme, cela débloquerait un prédicteur fort aujourd'hui inexploitable faute de données.

---

# Enrichissement complémentaire : NLP et récence

Reproductible via `python src/enrichissement_nlp_recence.py`.

## 6. NLP sur les commentaires d'anomalie

Le champ « Commentaire Anomalie » (texte libre) est renseigné pour ~7 % des interventions,
mais y concentre un signal utile (remplacement, vétuste, défaut, porte, poulie…). On en tire
des variables par familles de mots-clés, agrégées par appareil sur la fenêtre d'observation.
Apport mesuré, en validation temporelle :

| Cible | + fiche technique | + NLP | Δ |
|---|---|---|---|
| Tout dépannage | 0,789 | 0,793 | +0,004 |
| Défaillance matérielle | 0,805 | **0,811** | +0,006 |

Gain modeste mais réel. La variable NLP la plus utile est le simple **nombre de commentaires**
laissés par les techniciens (proxy de l'attention manuelle portée à l'appareil).

## 7. Récence / tendance (table des pannes répétitives) : un finding négatif

Des variables de récence et de tendance ont été dérivées de `Pannes_repetitives.xlsx`
(jours depuis la dernière panne, pannes sur 90 jours, niveau de répétition max, etc.),
calculées sur la fenêtre d'observation.

Résultat : **elles n'améliorent pas la généralisation** (−0,006 à −0,007), alors même que
« jours depuis la dernière panne » ressort individuellement comme une variable importante.
Explication : cette information est **déjà largement captée** par les comptages de dépannages
existants ; les ajouter introduit surtout de la redondance. Ces variables ne sont donc pas
retenues dans le modèle final. C'est un enseignement méthodologique utile : ajouter des données
n'améliore pas mécaniquement un modèle ; la sélection de variables compte.

## 8. Modèle final retenu

**base + fiche technique (charge, niveaux) + NLP**, forêt aléatoire, validation temporelle :
**AUC = 0,811** sur la défaillance matérielle (0,793 sur tout dépannage).
