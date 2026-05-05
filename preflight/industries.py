"""Industry-specific mandatory legal mentions (French regulatory).

Each `IndustryRule` declares:

* `required_phrases`: every phrase must be present (fuzzy match).
* `any_of_groups`: each group is a list of equivalent phrases; at least
  one phrase from each group must be present.
* `regex_requirements`: list of (label, regex) — each pattern must match
  the normalized text at least once. Used for things like CO2 emissions
  data where the value is variable.

"Général" is the no-extra-rules case; the universal advertiser/offer/
printer checks still apply, but no industry-specific phrase is required.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from preflight.text_normalize import normalize


@dataclass(frozen=True)
class IndustryRule:
    name: str
    required_phrases: tuple[str, ...] = ()
    any_of_groups: tuple[tuple[str, ...], ...] = ()
    regex_requirements: tuple[tuple[str, re.Pattern[str]], ...] = field(
        default=()
    )
    detection_keywords: tuple[str, ...] = ()


_AUTOMOBILES_CO2_RE = re.compile(
    r"\d+\s*(?:[\.,]\d+)?\s*g\s*(?:de\s*)?co2\s*/?\s*km",
    re.IGNORECASE,
)


INDUSTRIES: dict[str, IndustryRule] = {
    "Général": IndustryRule(name="Général"),
    "Alcool": IndustryRule(
        name="Alcool",
        required_phrases=(
            "L'abus d'alcool est dangereux pour la santé, à consommer avec modération.",
        ),
        detection_keywords=(
            "alcool", "biere", "vin", "whisky", "champagne", "spiritueux",
            "brasserie", "cognac", "cidre", "rhum", "vodka", "calvados",
            "aperitif", "liqueur",
        ),
    ),
    "Alimentation": IndustryRule(
        name="Alimentation",
        any_of_groups=(
            (
                "Pour votre santé, mangez au moins cinq fruits et légumes par jour",
                "Pour votre santé, pratiquez une activité physique régulière",
            ),
        ),
        detection_keywords=(
            "surgele", "epicerie", "confiserie", "gastronomie", "cereales",
            "yaourt", "fromage", "charcuterie", "boulangerie", "dietetique",
        ),
    ),
    "Compléments alimentaires": IndustryRule(
        name="Compléments alimentaires",
        required_phrases=(
            "À utiliser dans le cadre d'une alimentation variée et équilibrée et d'un mode de vie sain.",
        ),
        detection_keywords=(
            "complement alimentaire", "vitamine", "mineral", "omega",
            "probiotique", "collagene", "curcuma", "spiruline", "nutritionnel",
        ),
    ),
    "Médicaments et dispositifs médicaux": IndustryRule(
        name="Médicaments et dispositifs médicaux",
        any_of_groups=(
            (
                "Lire attentivement la notice",
                "Demandez conseil à votre pharmacien",
                "Si les symptômes persistent, consultez votre médecin",
                "Ce dispositif médical est un produit de santé réglementé qui porte, au titre de cette réglementation, le marquage CE",
            ),
        ),
        detection_keywords=(
            "medicament", "pharmacie", "ordonnance", "posologie", "dosage",
            "notice", "traitement medical", "dispositif medical", "labo",
        ),
    ),
    "Jeux d'argent et de hasard": IndustryRule(
        name="Jeux d'argent et de hasard",
        required_phrases=(
            "Jouer comporte des risques : endettement, isolement, dépendance. Appelez le 09-74-75-13-13 (appel non surtaxé).",
        ),
        detection_keywords=(
            "jeux", "pari", "mise", "casino", "loterie", "tierce",
            "jackpot", "fdj", "pmu", "pronostic",
        ),
    ),
    "Automobiles": IndustryRule(
        name="Automobiles",
        required_phrases=(
            "Pour votre sécurité, respectez les limitations de vitesse.",
        ),
        any_of_groups=(
            (
                "Pour les trajets courts, privilégiez la marche ou le vélo.",
                "Pensez à covoiturer.",
                "Au quotidien, prenez les transports en commun.",
            ),
        ),
        regex_requirements=(("Émissions CO2 (g/km)", _AUTOMOBILES_CO2_RE),),
        detection_keywords=(
            "voiture", "automobile", "vehicule", "moteur", "conduite",
            "electrique", "hybride", "berline", "suv", "citadine", "carburant",
        ),
    ),
    "Prêts à la consommation": IndustryRule(
        name="Prêts à la consommation",
        required_phrases=(
            "Un crédit vous engage et doit être remboursé. Vérifiez vos capacités de remboursement avant de vous engager.",
        ),
        detection_keywords=(
            "credit", "pret", "taux", "mensualite", "emprunt",
            "financement", "remboursement", "taeg",
        ),
    ),
    "Produits financiers": IndustryRule(
        name="Produits financiers",
        any_of_groups=(
            (
                "Les performances passées ne préjugent pas des performances futures",
                "Les performances passées ne sont pas un indicateur fiable des performances futures",
            ),
            (
                "Investir comporte des risques",
                "Les investissements présentent un risque de perte en capital",
                "Risque de perte en capital",
            ),
        ),
        detection_keywords=(
            "placement", "investissement", "epargne", "rendement",
            "portefeuille", "actions", "obligations", "bourse", "dividende",
        ),
    ),
    "Assurances": IndustryRule(
        name="Assurances",
        required_phrases=(
            "Un contrat d'assurance vous engage et doit être respecté. Vérifiez vos capacités à en respecter les termes.",
        ),
        detection_keywords=(
            "assurance", "garantie", "sinistre", "prime",
            "cotisation", "couverture", "indemnite",
        ),
    ),
    "Jouets": IndustryRule(
        name="Jouets",
        any_of_groups=(
            (
                "Ne convient pas aux enfants de moins de 36 mois",
                "Ne convient pas aux enfants de moins de 3 ans",
                "Attention. Ne convient pas aux enfants de moins de",
            ),
        ),
        detection_keywords=(
            "jouet", "figurine", "puzzle", "peluche", "jeu enfant", "jouets enfants",
        ),
    ),
}


INDUSTRY_NAMES = list(INDUSTRIES.keys())


def get_industry(name: str) -> IndustryRule:
    return INDUSTRIES.get(name, INDUSTRIES["Général"])


def detect_industry(text: str) -> tuple[str, float]:
    """Return (industry_name, confidence 0–1). Falls back to 'Général'."""
    norm = normalize(text)
    best_name = "Général"
    best_hits = 0

    for name, rule in INDUSTRIES.items():
        if name == "Général" or not rule.detection_keywords:
            continue
        hits = sum(1 for kw in rule.detection_keywords if kw in norm)
        if hits > best_hits:
            best_hits = hits
            best_name = name

    confidence = min(best_hits / 3.0, 1.0)  # 3 keyword hits = full confidence
    return best_name, confidence


__all__ = ["IndustryRule", "INDUSTRIES", "INDUSTRY_NAMES", "get_industry", "detect_industry"]
