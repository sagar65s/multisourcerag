from app.rag.query_router import QueryMode, route_query


def test_routes_current_question_to_web() -> None:
    assert route_query("What is the latest AI update?") == QueryMode.WEB


def test_routes_private_current_comparison_to_both() -> None:
    assert route_query("Compare my PDF with current research") == QueryMode.BOTH


def test_explicit_mode_wins() -> None:
    assert route_query("today", QueryMode.DEEP_RESEARCH) == QueryMode.DEEP_RESEARCH


def test_volatile_role_and_version_questions_require_web() -> None:
    assert route_query("Who is the CEO of Example Corp?") == QueryMode.WEB
    assert route_query("What version is the current stable release?") == QueryMode.WEB


def test_general_question_without_private_workspace_uses_general_chat() -> None:
    assert route_query("Explain retrieval augmented generation", has_private=False) == QueryMode.GENERAL


def test_deep_research_phrase_routes_to_dedicated_workflow() -> None:
    assert route_query("Create a comprehensive investigation of AI safety") == QueryMode.DEEP_RESEARCH
