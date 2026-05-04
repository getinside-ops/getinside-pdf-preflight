from preflight.industries import INDUSTRIES, INDUSTRY_NAMES, get_industry


EXPECTED = {
    "Général",
    "Alcool",
    "Alimentation",
    "Compléments alimentaires",
    "Médicaments et dispositifs médicaux",
    "Jeux d'argent et de hasard",
    "Automobiles",
    "Prêts à la consommation",
    "Produits financiers",
    "Assurances",
    "Jouets",
}


def test_all_eleven_industries_present():
    assert EXPECTED == set(INDUSTRIES)
    assert set(INDUSTRY_NAMES) == EXPECTED


def test_general_has_no_required_rules():
    rule = get_industry("Général")
    assert rule.required_phrases == ()
    assert rule.any_of_groups == ()
    assert rule.regex_requirements == ()


def test_alcool_has_canonical_phrase():
    rule = get_industry("Alcool")
    assert any("modération" in p for p in rule.required_phrases)


def test_alimentation_has_two_alternatives():
    rule = get_industry("Alimentation")
    assert len(rule.any_of_groups) == 1
    assert len(rule.any_of_groups[0]) == 2


def test_automobiles_has_co2_regex():
    rule = get_industry("Automobiles")
    labels = [label for label, _ in rule.regex_requirements]
    assert any("CO2" in lbl for lbl in labels)
    pattern = rule.regex_requirements[0][1]
    assert pattern.search("Émissions: 142 g CO2/km")
    assert pattern.search("142g co2 / km")
    assert pattern.search("142g de CO2/km")
    assert not pattern.search("aucune donnée")


def test_unknown_industry_falls_back_to_general():
    rule = get_industry("Inexistante")
    assert rule.name == "Général"
