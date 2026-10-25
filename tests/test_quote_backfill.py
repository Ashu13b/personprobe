from engine.quote_backfill import best_quote, collect_claims_needing_quotes
from engine.evidence import apply_quote_candidates
from engine.models import Claim, PersonProfile


def test_best_quote_matches_paraphrase_with_date_normalization():
    page = (
        "Hisar, Dec 11 (PTI) 'Hisar Gaurav', the first cloned calf born at the ICAR-Central Institute for "
        "Research on Buffaloes in Hisar, turned seven on Sunday. The male buffalo weighs 950 kg. "
        "Principal investigator Prem Singh Yadav said the project continues."
    )
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
        Claim(
            text="a",
            field="x",
            source_url="https://a",
            draft_approved=True,
            settled_quote="q",
        ),
        Claim(text="b", field="x", source_url="https://b", draft_approved=True),
        Claim(text="c", field="x", source_url="https://c", draft_approved=False),
        Claim(text="d", field="x", draft_approved=True),
    ]
    assert collect_claims_needing_quotes(claims) == [1]


def test_apply_quote_candidates_requires_approved_source_bound_claim():
    profile = PersonProfile(
        name="Test Subject",
        claims=[
            Claim(
                text="approved",
                field="x",
                source_url="https://source",
                draft_approved=True,
            ),
            Claim(text="unapproved", field="x", source_url="https://source"),
            Claim(text="unsourced", field="x", draft_approved=True),
        ],
    )
    result = apply_quote_candidates(
        profile,
        [
            {
                "claim_index": 0,
                "source_url": "https://source",
                "quote": "A sufficiently long source quote.",
            },
            {
                "claim_index": 1,
                "source_url": "https://source",
                "quote": "A sufficiently long source quote.",
            },
            {"claim_index": 2, "quote": "A sufficiently long source quote."},
        ],
        "agent",
    )
    assert result["updated"] == 1
    assert profile.claims[0].settled_quote is not None
    assert profile.claims[1].settled_quote is None
    assert profile.claims[2].settled_quote is None
