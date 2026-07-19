"""Context-budget features added in 0.3.0 (WI-P4, P5, P6).

Measured against live law.go.kr on 2026-07-19, in bytes of the emitted envelope:

    load-delegated-criteria --budget standard   513,570
    load-institutional-system --budget standard 396,609
    get-law (139 articles, no --article)        276,748
    get-case (one decision)                      82,700

Nothing warned about any of it, and the only narrowing tool was `--article`,
which presumes you already know which article you want. Reading a whole statute
to find that out is the expensive way to ask a cheap question. So: a map
(`--toc`), a précis (`--brief`), and a signal when neither was used.
"""

import json

import pytest

from moleg_api import LawToc, MolegApi
from moleg_api._cli.payload_size import LARGE_PAYLOAD_CHARS, large_payload_signals
from moleg_api._cli.brief_mode import brief_dropped, to_brief
from moleg_api._normalization.article_units import article_text_value
from moleg_api.cli import main
from moleg_api.models import (
    ArticleText,
    JudicialDecisionIdentity,
    JudicialDecisionText,
    LawIdentity,
    LawText,
)


def _identity():
    return LawIdentity(law_id="011357", name="개인정보 보호법", basis="effective", effective_date="20251002")


def _article(number, title, *, kind="조문", text="본문", deleted=False, moved_to=None):
    return ArticleText(
        identity=_identity(), article=number, title=title, text=text,
        article_kind=kind, is_deleted=deleted, moved_to=moved_to,
    )


class TocApi:
    def __init__(self, articles):
        self._law = LawText(identity=_identity(), articles=articles)

    def get_law(self, *_args, **_kwargs):
        return self._law

    def get_law_toc(self, *args, **kwargs):
        from moleg_api._laws.api_law_toc import LawTocMixin

        return LawTocMixin.get_law_toc(self, *args, **kwargs)


# --- WI-P4: table of contents ---------------------------------------------------


def test_toc_keeps_the_map_and_drops_the_text():
    api = TocApi([_article("제1조", None, kind="전문", text="제1장 총칙"),
                  _article("제1조", "목적", text="이 법은 …" * 200)])
    toc = api.get_law_toc("011357")
    assert isinstance(toc, LawToc)
    rendered = json.dumps(toc.to_dict(), ensure_ascii=False)
    assert "이 법은" not in rendered, "the text is the thing a map exists to avoid carrying"
    assert "제1장 총칙" in rendered and "목적" in rendered


def test_heading_rows_do_not_count_as_articles():
    # law.go.kr threads chapter headings through the article list tagged 전문,
    # reusing a neighbouring article number. Counting them inflates the number a
    # caller uses to judge whether a full load is affordable.
    api = TocApi([_article("제1조", None, kind="전문", text="제1장 총칙"),
                  _article("제1조", "목적"),
                  _article("제2조", "정의")])
    toc = api.get_law_toc("011357")
    assert toc.article_count == 2
    assert len(toc.entries) == 3
    assert [e.entry_kind for e in toc.entries] == ["heading", "article", "article"]


def test_deleted_and_moved_articles_stay_visible():
    api = TocApi([_article("제8조", None, deleted=True), _article("제9조", "이동", moved_to="제10조")])
    toc = api.get_law_toc("011357")
    assert toc.entries[0].is_deleted is True
    assert toc.entries[1].moved_to == "제10조"


def test_placeholder_move_target_is_not_passed_through():
    # 제0조 is the source's "no real destination" sentinel; forwarding it sends a
    # caller chasing an article that does not exist.
    api = TocApi([_article("제31조의2", "제목", moved_to="제0조")])
    assert api.get_law_toc("011357").entries[0].moved_to is None


def test_empty_fields_are_omitted_so_the_map_stays_small():
    api = TocApi([_article("제3조", "개인정보 보호 원칙")])
    entry = api.get_law_toc("011357").entries[0].to_dict()
    assert entry == {"article": "제3조", "title": "개인정보 보호 원칙", "entry_kind": "article"}


def test_nested_heading_arrays_are_flattened_not_repr_d():
    """A row carrying both a 장 and a 절 returns a nested array; `str()` on that
    yielded `[['제3장 …', '제1절 …']]`, which then travelled as if it were the
    statute's own wording — wrong in a way a reader cannot detect."""
    assert article_text_value([["제3장 개인정보의 처리", "제1절 수집"]]) == "제3장 개인정보의 처리\n제1절 수집"
    assert article_text_value("제1장 총칙") == "제1장 총칙"
    assert article_text_value(None) == ""


def test_toc_envelope_says_it_is_not_citable(capsys):
    api = TocApi([_article("제1조", "목적")])
    code = main(["get-law", "--law", "011357", "--toc"], api=api)
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    assert out["kind"] == "law_toc_map"
    assert any("목차는 본문이 아님" in d for d in out["discipline"])
    assert any("get-article" in n["cmd"] for n in out["next"])


# --- WI-P5: large-payload guard --------------------------------------------------


def test_guard_is_quiet_below_the_threshold():
    flags, discipline = large_payload_signals("get-law", LARGE_PAYLOAD_CHARS - 1)
    assert flags == {} and discipline == []


def test_guard_fires_above_it_with_command_specific_advice():
    flags, discipline = large_payload_signals("get-law", LARGE_PAYLOAD_CHARS + 1, {"articles": 139})
    assert flags["large_payload"] == {"chars": LARGE_PAYLOAD_CHARS + 1, "articles": 139}
    assert "--toc" in discipline[0]

    _, case_discipline = large_payload_signals("get-case", 100_000)
    assert "--brief" in case_discipline[0]

    _, loader_discipline = large_payload_signals("load-delegated-criteria", 300_000)
    assert "--budget minimal" in loader_discipline[0]


def test_unknown_commands_still_get_generic_advice():
    """The guard measures output, so a command added later is covered on arrival —
    but only if the fallback says something useful instead of nothing."""
    _, discipline = large_payload_signals("some-future-loader", 500_000)
    assert discipline and "범위를 좁힐" in discipline[0]


@pytest.mark.parametrize("command", ["search-laws", "search-cases", "expand-legal-query", "find-comparable-mechanisms"])
def test_searches_are_exempt(command):
    # Candidate breadth is what resolves ambiguity — 20 hits costs ~18,000
    # characters, and firing there would make the signal noise on the one family
    # where the size is the intended behaviour (§3.1 keeps display=20).
    flags, _ = large_payload_signals(command, 500_000)
    assert flags == {}


# --- WI-P6: brief mode -----------------------------------------------------------


def _decision(**overrides):
    fields = {
        "holdings": "판시사항", "summary": "결정요지",
        "full_text": "전문 본문", "text": "판례 전문",
    }
    fields.update(overrides)
    return JudicialDecisionText(
        identity=JudicialDecisionIdentity(
            decision_id="193332", title="판례", source_type="case", source_target="prec"
        ),
        **fields,
    )


def test_brief_blanks_the_full_body_and_keeps_the_precis():
    brief = to_brief(_decision())
    # Each field resets to its own declared default, not a blanket "": `text: str`
    # is empty-string-absent, `full_text: str | None` is None-absent. Blanking a
    # nullable field to "" turns "not loaded" into "loaded and empty", which a
    # caller reads as a fact about the document rather than about the request.
    assert brief.text == "" and brief.full_text is None
    assert brief.summary == "결정요지" and brief.holdings == "판시사항"


def test_brief_returns_the_same_type():
    # A narrower type would break every consumer's field access for a difference
    # that belongs on the envelope, not in a second shape of the same thing.
    assert isinstance(to_brief(_decision()), JudicialDecisionText)


def test_withheld_list_reports_only_what_was_actually_there():
    # Claiming brief mode withheld a section the source never had sends the caller
    # looking for something that does not exist.
    assert brief_dropped(_decision()) == ["text", "full_text"]
    assert brief_dropped(_decision(full_text=None)) == ["text"]


def test_brief_envelope_forbids_verbatim_citation(capsys):
    class CaseApi:
        def get_case(self, *_a, **_k):
            return _decision()

    code = main(["get-case", "--id", "193332", "--brief"], api=CaseApi())
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    assert out["flags"]["brief"]["withheld"] == ["text", "full_text"]
    assert any("축자 인용은" in d for d in out["discipline"])
    assert out["data"]["text"] == "" and out["data"]["summary"] == "결정요지"


def test_without_brief_nothing_is_withheld(capsys):
    class CaseApi:
        def get_case(self, *_a, **_k):
            return _decision()

    main(["get-case", "--id", "193332"], api=CaseApi())
    out = json.loads(capsys.readouterr().out)
    assert "brief" not in out.get("flags", {})
    assert out["data"]["text"] == "판례 전문"
