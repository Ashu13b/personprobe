from engine.quote_backfill import best_quote, collect_claims_needing_quotes
from engine.models import Claim


def test_best_quote_matches_paraphrase_with_date_normalization():
    page = ("Hisar, Dec 11 (PTI) 'Hisar Gaurav', the first cloned calf born at the ICAR-Central Institute for "
            "Research on Buffaloes in Hisar, turned seven on Sunday. The male buffalo weighs 950 kg. "
            "Principal investigator Prem Singh Yadav said the project continues.")
    claim = "Hisar Gaurav, the first cloned calf born at ICAR-CIRB Hisar, turned seven in December 2022."
    quote, score = best_quote(claim, page)
    assert quote is not None and "turned seven" in quote
    assert score >= 0.30


def test_best_quote_matches_birth_date_across_date_formats():
    page = "Staff record: Born on April 10, 1963 in Village Nimoth, Tehsil & District Rewari, Haryana. Joined 1993."
    claim = "Born on 10 April 1963 in Village Nimoth, Tehsil & District Rewari, Haryana, India"
    quote, score = best_quote(claim, page)
    assert quote is not None and "1963" in quote
    assert score >= 0.3


def test_best_quote_refuses_when_no_support():
    page = "The weather was pleasant and the institute canteen served tea at noon."
    claim = "Yadav received the Nanaji Deshmukh team award in 2020 at Navsari."
    quote, score = best_quote(claim, page)
    assert quote is None


def test_collect_claims_needing_quotes_filters():
    claims = [
        Claim(text="a", field="x", source_url="https://a", draft_approved=True, settled_quote="q"),
        Claim(text="b", field="x", source_url="https://b", draft_approved=True),
        Claim(text="c", field="x", source_url="https://c", draft_approved=False),
        Claim(text="d", field="x", draft_approved=True),
    ]
    assert collect_claims_needing_quotes(claims) == [1]
