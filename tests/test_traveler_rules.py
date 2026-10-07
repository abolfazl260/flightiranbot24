from datetime import date, timedelta

from flightiran.interfaces.telegram.traveler_rules import render_rule
from flightiran.modules.traveler_rules import RuleArticle, RulesRepository


def article(**kwargs):
    values = dict(
        id="customs-1",
        title="Customs",
        body="No <script>",
        category="customs",
        countries=("IR",),
        source_url="https://source.test",
        checked_on=date.today(),
        valid_until=date.today() + timedelta(days=1),
    )
    values.update(kwargs)
    return RuleArticle(**values)


def test_search_filters_category_country_and_active_expiry():
    repo = RulesRepository(
        [
            article(),
            article(id="old", valid_until=date.today() - timedelta(days=1)),
            article(id="off", active=False),
        ]
    )
    assert [item.id for item in repo.search("custom", category="customs", country="IR")] == [
        "customs-1"
    ]
    assert repo.search("custom", country="DE") == []


def test_render_is_escaped_and_source_backed():
    output = render_rule(article())
    assert "&lt;script&gt;" in output
    assert "source.test" in output
