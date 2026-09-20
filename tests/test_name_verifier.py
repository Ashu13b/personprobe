"""Tests for the Name Verification and Disambiguation Gate."""
from engine.name_verifier import generate_name_variants, verify_name_in_content


def test_generate_name_variants_western():
    variants = generate_name_variants("Alan Mathison Turing")
    assert "Alan Mathison Turing" in variants
    assert "Alan Turing" in variants
    assert "A. M. Turing" in variants
    assert "A. Turing" in variants
    assert "Dr. Alan Mathison Turing" in variants


def test_generate_name_variants_indic():
    variants = generate_name_variants("Prem Singh Yadav", nationality="Indian")
    assert "Prem Singh Yadav" in variants
    assert "P. S. Yadav" in variants
    assert "प्रेम सिंह यादव" in variants
    assert "पी. एस. यादव" in variants
    assert "Dr. Prem Singh Yadav" in variants


def test_verify_name_in_content_exact_and_initials():
    text = "The breakthrough buffalo research was supervised by Dr. P. S. Yadav at the research institute."
    res = verify_name_in_content("Prem Singh Yadav", text, affiliation="CIRB")
    assert res.matched is True
    assert "P. S. Yadav" in res.variant
    assert "breakthrough buffalo research" in res.snippet


def test_verify_name_in_content_devanagari():
    text = "हिसार के केंद्रीय भैंस अनुसंधान संस्थान में प्रधान वैज्ञानिक डॉ. प्रेम सिंह यादव ने क्लोनिंग तकनीक पर व्याख्यान दिया।"
    res = verify_name_in_content("Prem Singh Yadav", text, affiliation="CIRB", nationality="Indian")
    assert res.matched is True
    assert "प्रेम सिंह यादव" in res.variant


def test_verify_name_no_match():
    text = "A conference on agricultural finance was held in New Delhi yesterday."
    res = verify_name_in_content("Prem Singh Yadav", text)
    assert res.matched is False
    assert res.reason == "no_name_match"


def test_verify_name_homonym_risk():
    text = "Prominent politician and MLA Prem Singh Yadav addressed a massive election rally today."
    res = verify_name_in_content(
        name="Prem Singh Yadav",
        text=text,
        affiliation="Central Institute for Research on Buffaloes",
        field="Animal biotechnology",
    )
    assert res.matched is True
    assert res.context_matched is False
    assert res.homonym_risk is True
    assert res.reason == "homonym_risk"
