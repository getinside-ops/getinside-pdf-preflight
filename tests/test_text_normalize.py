from preflight.text_normalize import fuzzy_contains, fuzzy_score, normalize


def test_normalize_strips_accents_and_lowercases():
    assert normalize("L'abus d'Alcool") == "l'abus d'alcool"
    assert normalize("Médicaments") == "medicaments"
    assert normalize("RÉGULIÈRE") == "reguliere"


def test_normalize_collapses_whitespace_and_typography():
    src = "Pour votre santé, mangez   au moins—cinq fruits"
    out = normalize(src)
    assert out == "pour votre sante, mangez au moins-cinq fruits"


def test_normalize_handles_curly_quotes():
    assert normalize("L’abus") == normalize("L'abus")
    assert normalize("“Test”") == '"test"'


def test_fuzzy_contains_exact_match():
    haystack = "Pour votre santé, mangez au moins cinq fruits et légumes par jour."
    needle = "Pour votre santé, mangez au moins cinq fruits et légumes par jour"
    assert fuzzy_contains(haystack, needle)


def test_fuzzy_contains_tolerates_ocr_noise():
    # Simulated OCR errors: missing accents, extra spaces, period drift
    haystack = "pour votre sante , mangez au moins cinq fruits et legumes par jour"
    needle = "Pour votre santé, mangez au moins cinq fruits et légumes par jour"
    assert fuzzy_contains(haystack, needle)


def test_fuzzy_contains_rejects_unrelated_text():
    haystack = "Cette publicité ne contient aucune mention obligatoire."
    needle = "L'abus d'alcool est dangereux pour la santé"
    assert not fuzzy_contains(haystack, needle)


def test_fuzzy_contains_empty_inputs():
    assert fuzzy_contains("anything", "") is True
    assert fuzzy_contains("", "needle") is False


def test_fuzzy_score_monotonic():
    haystack = "L'abus d'alcool est dangereux pour la santé"
    perfect = fuzzy_score(haystack, "L'abus d'alcool est dangereux pour la santé")
    partial = fuzzy_score(haystack, "L'abus d'alcool")
    unrelated = fuzzy_score(haystack, "Pour votre sécurité respectez les limitations")
    assert perfect >= partial > unrelated
