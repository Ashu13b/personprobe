from engine.models import Source
from engine.workflow import advance_source_stage


def test_sources_start_discovered_and_advance_one_gate_at_a_time():
    source = Source(url="https://example.test", title="Example", publisher="Example")
    assert source.workflow_stage == "discovered"
    assert not advance_source_stage(source, "identity_checked")
    assert advance_source_stage(source, "retrieved")
    assert advance_source_stage(source, "identity_checked")
    assert advance_source_stage(source, "provenance_checked")
    assert not advance_source_stage(source, "provenance_checked")
