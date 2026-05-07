"""Tests for the text-based checks (advertiser, offer, printer, industry)."""

from __future__ import annotations

import pytest

from preflight.checks import Severity
from preflight.checks.advertiser import check_advertiser, validate_siren
from preflight.checks.industry import check_industry
from preflight.checks.offer import check_offer
from preflight.checks.printer import GETINSIDE_PRINTER_MENTION, check_printer


COMPLIANT_TEXT = """
Getinside SAS — Capital social 50 000 euros.
Siège social: 12 rue de l'Exemple, 75001 Paris.
RCS Paris 100 000 009.
Offre valable jusqu'au 31/12/2026. Code promo : HELLO2026.
""" + GETINSIDE_PRINTER_MENTION + "."


def _has_error(results) -> bool:
    return any(r.severity is Severity.ERROR for r in results)


# --- Advertiser ---------------------------------------------------------------


def test_advertiser_compliant():
    results = check_advertiser(COMPLIANT_TEXT)
    assert not _has_error(results), [r.message for r in results if r.severity is Severity.ERROR]


def test_advertiser_detects_legal_form():
    results = check_advertiser(COMPLIANT_TEXT)
    infos = [r for r in results if r.severity is Severity.INFO]
    assert any("SAS" in r.message for r in infos)


def test_advertiser_detects_capital():
    results = check_advertiser(COMPLIANT_TEXT)
    infos = [r for r in results if r.severity is Severity.INFO]
    assert any("capital social" in r.message.lower() for r in infos)


def test_advertiser_detects_rcs():
    results = check_advertiser(COMPLIANT_TEXT)
    infos = [r for r in results if r.severity is Severity.INFO]
    assert any("RCS" in r.message for r in infos)


def test_advertiser_missing_rcs():
    text = COMPLIANT_TEXT.replace("RCS Paris 100 000 009", "")
    results = check_advertiser(text)
    assert _has_error(results)


def test_advertiser_missing_legal_form():
    text = COMPLIANT_TEXT.replace(" SAS", "")
    results = check_advertiser(text)
    assert _has_error(results)


def test_advertiser_missing_capital():
    text = COMPLIANT_TEXT.replace("Capital social 50 000 euros", "")
    results = check_advertiser(text)
    assert _has_error(results)


# --- SIREN validation ----------------------------------------------------------


def test_validate_siren_valid():
    assert validate_siren("100000009") is True
    assert validate_siren("123456782") is True


def test_validate_siren_invalid():
    assert validate_siren("123456789") is False
    assert validate_siren("999999999") is False


def test_validate_siren_invalid_length():
    assert validate_siren("12345678") is False
    assert validate_siren("1234567890") is False
    assert validate_siren("abc") is False


def test_validate_siren_with_spaces():
    assert validate_siren("100 000 009") is True
    assert validate_siren("123 456 789") is False


# --- Offer --------------------------------------------------------------------


def test_offer_detects_numeric_date():
    results = check_offer("Offre valable jusqu'au 31/12/2026.")
    infos = [r for r in results if r.severity is Severity.INFO]
    assert any("31/12/2026" in r.message for r in infos)


def test_offer_detects_french_text_date():
    results = check_offer("Offre valable jusqu'au 31 décembre 2026.")
    infos = [r for r in results if r.severity is Severity.INFO]
    assert any("decembre" in r.message or "décembre" in r.message for r in infos)


def test_offer_no_date_gives_warning():
    results = check_offer("Aucune date ici. Aucun code non plus.")
    assert any(r.severity is Severity.WARNING for r in results)
    assert not _has_error(results)


def test_offer_detects_promo_code():
    results = check_offer("Code promo : HELLO2026")
    infos = [r for r in results if r.severity is Severity.INFO]
    assert any("HELLO2026" in r.message for r in infos)


@pytest.mark.parametrize("text", [
    "Avec le code : SAGETCAATS",
    "Avec le code SAGETCAATS",
    "Code remise : SAVE20",
    "Code réduction : PROMO50",
    "Code reduction : PROMO50",
    "Code avantage : VIP2026",
    "Code exclusif : INSIDER",
    "Utilisez le code : BIENVENUE",
    "Utilisez code WELCOME",
    "Votre code : FIDELE",
    "Mon code : MONCODE1",
    "Ton code : TONCODE1",
])
def test_offer_detects_promo_code_various_phrasings(text):
    code = text.split()[-1].rstrip(".,;")
    results = check_offer(text)
    infos = [r for r in results if r.severity is Severity.INFO]
    assert any(code in r.message for r in infos), f"Code not detected in: {text!r}"


def test_offer_no_promo_code_is_info_not_error():
    results = check_offer("Offre valable jusqu'au 31/12/2026.")
    assert not _has_error(results)
    assert not any(r.severity is Severity.WARNING and "code" in r.message.lower() for r in results)


def test_offer_compliant_full():
    results = check_offer(COMPLIANT_TEXT)
    assert not _has_error(results)


# --- Printer ------------------------------------------------------------------


def test_printer_getinside_compliant():
    results = check_printer(COMPLIANT_TEXT, "Imprimé par getinside")
    assert not _has_error(results)


def test_printer_getinside_missing_mention():
    results = check_printer("aucune mention", "Imprimé par getinside")
    assert _has_error(results)


def test_printer_self_print_advisory_only():
    results = check_printer("aucune mention", "Imprimé par la marque")
    assert not _has_error(results)


# --- Industry -----------------------------------------------------------------


def test_industry_general_no_check():
    results = check_industry("rien d'obligatoire", "Général")
    assert not _has_error(results)


def test_industry_alcool_compliant():
    text = "L'abus d'alcool est dangereux pour la santé, à consommer avec modération."
    results = check_industry(text, "Alcool")
    assert not _has_error(results)


def test_industry_alcool_missing():
    results = check_industry("nothing here", "Alcool")
    assert _has_error(results)


def test_industry_alimentation_either_phrase_works():
    text = "Pour votre santé, pratiquez une activité physique régulière."
    results = check_industry(text, "Alimentation")
    assert not _has_error(results)


def test_industry_jeux_argent_phone_number_required():
    text = (
        "Jouer comporte des risques : endettement, isolement, dépendance. "
        "Appelez le 09-74-75-13-13 (appel non surtaxé)."
    )
    results = check_industry(text, "Jeux d'argent et de hasard")
    assert not _has_error(results)


def test_industry_automobiles_full():
    text = (
        "Émissions: 142 g CO2/km. "
        "Pour votre sécurité, respectez les limitations de vitesse. "
        "Pensez à covoiturer."
    )
    results = check_industry(text, "Automobiles")
    assert not _has_error(results)


def test_industry_automobiles_missing_co2():
    text = (
        "Pour votre sécurité, respectez les limitations de vitesse. "
        "Pensez à covoiturer."
    )
    results = check_industry(text, "Automobiles")
    assert _has_error(results)


def test_industry_jouets_age_warning():
    text = "Attention. Ne convient pas aux enfants de moins de 36 mois."
    results = check_industry(text, "Jouets")
    assert not _has_error(results)
