from src.job_utils import normalize_job_url, stable_job_id


def test_normalize_job_url_handles_missing_href():
    assert normalize_job_url(None, "https://example.com") is None
    assert normalize_job_url("", "https://example.com") is None


def test_normalize_job_url_makes_relative_url_absolute_and_strips_query():
    assert (
        normalize_job_url("/job/123?tracking=abc#details", "https://example.com")
        == "https://example.com/job/123"
    )


def test_stable_job_id_is_deterministic():
    first = stable_job_id("dice", "https://example.com/job/123", "Engineer", "Acme")
    second = stable_job_id("dice", "https://example.com/job/123", "Engineer", "Acme")
    assert first == second
    assert first.startswith("dice_")
