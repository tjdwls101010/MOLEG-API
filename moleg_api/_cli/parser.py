from __future__ import annotations

from .foundation import *
from .._version import __version__
from .signals_meta import parse_as_of

def _add_law(p: argparse.ArgumentParser, required: bool = True) -> None:
    p.add_argument("--law", required=required, help="law_id (search-laws가 준 값). 법령명을 주면 needs_search_first로 막힘.")


def _add_basis(p: argparse.ArgumentParser) -> None:
    p.add_argument("--basis", choices=["effective", "promulgated"], default="effective")


def _add_as_of(p: argparse.ArgumentParser) -> None:
    p.add_argument("--as-of", dest="as_of", default=None, metavar="YYYY-MM-DD", help="기준일(현재 시행 여부·역사적 시점 조회).")


def _add_articles(p: argparse.ArgumentParser, required: bool = False) -> None:
    p.add_argument("--article", dest="article", action="append", default=[], required=required, help="조문(예: 제3조). 반복 지정 가능.")


def _add_brief(p: argparse.ArgumentParser) -> None:
    p.add_argument("--brief", action="store_true",
                   help="전문(text/full_text) 없이 요지·판시사항·참조 관계만. 인용은 전문 로드 후.")


def _add_budget(p: argparse.ArgumentParser) -> None:
    p.add_argument("--budget", choices=["minimal", "standard", "broad"], default="standard")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="moleg",
        description="법제처 law.go.kr 법령 자료 조회 CLI. 항상 JSON 엔벨로프 1개를 stdout으로 출력.",
    )
    parser.add_argument("--raw", action="store_true", help="원본 소스 payload(raw)까지 직렬화(디버그).")
    parser.add_argument(
        "--version",
        action="version",
        version=f"moleg-api {__version__}",
        help="실행 중인 moleg-api 버전을 출력하고 종료(엔벨로프의 version과 같은 값).",
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    sub.add_parser("catalog", help="전체 서브커맨드·규약·kind 목록을 한 번에.")

    # ---- searches / planning ------------------------------------------- #
    p = sub.add_parser("search-laws", help="현행/공포 법령 신원 후보 검색.")
    p.add_argument("query"); _add_as_of(p); _add_basis(p)
    p.add_argument("--law-type", dest="law_type", default=None)
    p.add_argument("--ministry", default=None); p.add_argument("--display", type=int, default=20)

    p = sub.add_parser("resolve-promulgated-law", help="공포 bridge(법명·공포번호·공포일)로 법령 신원 확정.")
    p.add_argument("--prom-law-nm", dest="prom_law_nm", default=None)
    p.add_argument("--prom-no", dest="prom_no", default=None)
    p.add_argument("--promulgation-dt", dest="promulgation_dt", default=None)

    p = sub.add_parser("search-administrative-rules", help="고시·훈령·예규 등 행정규칙 검색.")
    p.add_argument("query"); p.add_argument("--ministry", default=None)
    p.add_argument("--rule-type", dest="rule_type", default=None)
    p.add_argument("--issued-on", dest="issued_on", default=None, help="발령일자 필터(시행일 아님).")
    p.add_argument("--include-history", dest="include_history", action="store_true")
    p.add_argument("--display", type=int, default=20)

    p = sub.add_parser("search-annex-forms", help="별표·서식 후보 검색.")
    p.add_argument("query")
    p.add_argument("--source", choices=["law", "administrative_rule"], default="law")
    p.add_argument("--search-scope", dest="search_scope", choices=["title", "source", "body"], default="title",
                   help="title=별표 제목 매칭(기본) / source=소관 법령명 매칭 / body=본문 전체. 제목으로 0건이면 source로 재시도.")
    p.add_argument("--annex-type", dest="annex_type", default=None)
    p.add_argument("--ministry", default=None); p.add_argument("--display", type=int, default=20)

    p = sub.add_parser("search-interpretations", help="법령해석례(법제처·부처) 검색.")
    p.add_argument("query")
    p.add_argument("--source", choices=["moleg", "ministry", "all", "all_ministries"], default="moleg")
    p.add_argument("--ministry", default=None)
    p.add_argument("--search-body", dest="search_body", action="store_true", help="제목이 아니라 본문(판시사항·주문·이유·해석 전문) 전체를 검색. doctrine·본문 키워드로 0건이면 이 옵션으로 재시도.")
    p.add_argument("--interpreted-on", dest="interpreted_on", default=None)
    p.add_argument("--display", type=int, default=20)

    p = sub.add_parser("search-cases", help="대법원·각급 판례 검색.")
    p.add_argument("query")
    p.add_argument("--court", choices=["all", "supreme", "lower"], default="all")
    p.add_argument("--court-name", dest="court_name", default=None)
    p.add_argument("--search-body", dest="search_body", action="store_true", help="제목이 아니라 본문(판시사항·주문·이유·해석 전문) 전체를 검색. doctrine·본문 키워드로 0건이면 이 옵션으로 재시도.")
    p.add_argument("--decided-on", dest="decided_on", default=None)
    p.add_argument("--case-number", dest="case_number", default=None)
    p.add_argument("--display", type=int, default=20)

    p = sub.add_parser("search-constitutional-decisions", help="헌재 결정 검색.")
    p.add_argument("query")
    p.add_argument("--search-body", dest="search_body", action="store_true", help="제목이 아니라 본문(판시사항·주문·이유·해석 전문) 전체를 검색. doctrine·본문 키워드로 0건이면 이 옵션으로 재시도.")
    p.add_argument("--decided-on", dest="decided_on", default=None)
    p.add_argument("--case-number", dest="case_number", default=None)
    p.add_argument("--display", type=int, default=20)

    p = sub.add_parser("search-committee-decisions", help="위원회 결정문 검색(개보위·공정위·금융위·인권위 등 12종).")
    p.add_argument("query", nargs="?", default=None, help="안건명·사건명 키워드(생략 시 최신 목록).")
    p.add_argument("--committee", required=True,
                   help="기관 코드: ppc(개인정보보호위) ftc(공정위) fsc(금융위) sfc(증선위) kcc(방통위) nhrck(인권위) acr(권익위) nlrc(노동위) eiac(고용보험심사위) iaciac(산재재심사위) oclt(중앙토지수용위) ecc(중앙환경분쟁조정위).")
    p.add_argument("--display", type=int, default=20)

    p = sub.add_parser("get-committee-decision", help="위원회 결정문 본문 로드(--brief면 요지만).")
    p.add_argument("--id", dest="identifier", required=True, help="decision_id(검색이 준 값).")
    p.add_argument("--committee", required=True, help="검색에 쓴 기관 코드와 동일해야 한다.")
    _add_brief(p)

    p = sub.add_parser("search-administrative-appeals", help="행정심판 재결례 검색(일반 + 특별심판 4종).")
    p.add_argument("query", nargs="?", default=None, help="사건명 키워드(생략 시 최신 목록).")
    p.add_argument("--tribunal", default="decc",
                   help="decc(일반 행정심판위) acr(권익위 특별) adap(소청심사위) tt(조세심판원) kmst(해양안전심판원).")
    p.add_argument("--display", type=int, default=20)

    p = sub.add_parser("get-administrative-appeal", help="행정심판 재결 본문 로드(--brief면 요지만).")
    p.add_argument("--id", dest="identifier", required=True)
    p.add_argument("--tribunal", default="decc", help="검색에 쓴 심판기관 코드와 동일해야 한다.")
    _add_brief(p)

    p = sub.add_parser("expand-legal-query", help="질의 확장·관련법/용어/조문 조사 계획.")
    p.add_argument("query"); p.add_argument("--display", type=int, default=5)
    p.add_argument("--no-websearch-hint", dest="no_websearch_hint", action="store_true")

    p = sub.add_parser("find-comparable-mechanisms", help="유사 법적 기제(제도) 탐색.")
    p.add_argument("concept"); p.add_argument("--display", type=int, default=5)

    # ---- loaders -------------------------------------------------------- #
    p = sub.add_parser("get-law", help="법령 본문 로드(--toc면 본문 없이 조문 목차만).")
    _add_law(p); _add_as_of(p); _add_basis(p); _add_articles(p)
    p.add_argument("--no-metadata", dest="no_metadata", action="store_true")
    p.add_argument("--toc", action="store_true",
                   help="본문 대신 조문 목차(장·절 표제 + 조번호·조제목 + 삭제/이동)만. 큰 법의 지도를 수 KB로.")

    p = sub.add_parser("get-article", help="조문 하나 로드.")
    _add_law(p); p.add_argument("article"); _add_as_of(p); _add_basis(p)

    p = sub.add_parser("load-article-context", help="조문 로드 + 이동/삭제 상태 해소.")
    _add_law(p); p.add_argument("article"); _add_as_of(p); _add_basis(p)
    p.add_argument("--no-follow-moved", dest="no_follow_moved", action="store_true")

    p = sub.add_parser("get-administrative-rule", help="행정규칙 본문 로드.")
    p.add_argument("--id", dest="identifier", required=True, help="serial_id(검색이 준 값).")
    _add_articles(p); p.add_argument("--no-metadata", dest="no_metadata", action="store_true")

    p = sub.add_parser("load-administrative-rule-context", help="행정규칙 로드 + 이동/삭제 해소.")
    p.add_argument("--id", dest="identifier", required=True)
    _add_articles(p); p.add_argument("--no-metadata", dest="no_metadata", action="store_true")
    p.add_argument("--no-follow-moved", dest="no_follow_moved", action="store_true")

    p = sub.add_parser("get-annex-form-body", help="별표·서식 본문 로드.")
    p.add_argument("--id", "--annex-id", dest="identifier", required=True, help="annex_id(검색이 준 값). --annex-id로도 받음.")
    p.add_argument("--source", choices=["law", "administrative_rule"], default="law")
    p.add_argument("--title", default=None)
    p.add_argument("--no-metadata", dest="no_metadata", action="store_true")
    p.add_argument("--no-structuring", dest="no_structuring", action="store_true")

    p = sub.add_parser("get-interpretation", help="법령해석례 본문 로드(--brief면 질의·회답만).")
    p.add_argument("--id", dest="identifier", required=True)
    p.add_argument("--source", choices=["moleg", "ministry", "all", "all_ministries"], default=None)
    p.add_argument("--ministry", default=None)
    p.add_argument("--no-metadata", dest="no_metadata", action="store_true")
    _add_brief(p)

    p = sub.add_parser("get-case", help="판례 본문 로드(--brief면 요지만).")
    p.add_argument("--id", dest="identifier", required=True)
    p.add_argument("--no-metadata", dest="no_metadata", action="store_true")
    _add_brief(p)

    p = sub.add_parser("get-constitutional-decision", help="헌재 결정 본문 로드(--brief면 요지만).")
    p.add_argument("--id", dest="identifier", required=True)
    p.add_argument("--no-metadata", dest="no_metadata", action="store_true")
    _add_brief(p)

    # ---- history / structure / delegation ------------------------------ #
    p = sub.add_parser("trace-law-history", help="개정 연혁 이벤트.")
    _add_law(p); p.add_argument("--article", default=None)
    p.add_argument("--date-from", dest="date_from", default=None)
    p.add_argument("--date-to", dest="date_to", default=None)

    p = sub.add_parser("get-revision-reason", help="특정 버전의 「개정이유 및 주요내용」·공포문 원문.")
    _add_law(p)
    p.add_argument("--mst", default=None, help="버전 MST(trace-law-history 이벤트의 identity.mst). 미지정이면 최신 버전.")
    p.add_argument("--as-of", dest="as_of", default=None, help="그 시점 시행 버전의 개정이유(YYYY-MM-DD/YYYYMMDD).")

    p = sub.add_parser("compare-law-versions", help="개정 전후 조문 문구 비교(소스 제공 전후 쌍).")
    _add_law(p); p.add_argument("--article", default=None)

    p = sub.add_parser("find-delegated-rules", help="위임 규정·하위 법령.")
    _add_law(p); p.add_argument("--article", default=None)

    p = sub.add_parser("get-law-structure", help="법령 체계도(lsStmd 계층).")
    _add_law(p); p.add_argument("--depth", type=int, default=0)

    # ---- authority / bundles ------------------------------------------- #
    p = sub.add_parser("load-authority-context", help="조문 범위 해석·판례·헌재 권위.")
    _add_law(p); _add_articles(p, required=True); p.add_argument("--query", default=None)
    _add_budget(p); _add_as_of(p)

    p = sub.add_parser("load-legal-context-bundle", help="넓은 질문의 staged 1차 로딩.")
    p.add_argument("--query", default=None)
    _add_law(p, required=False); _add_articles(p)
    p.add_argument("--mode", choices=["question", "promulgated_bill", "statute_review"], default="question")
    _add_budget(p); _add_as_of(p)
    p.add_argument("--prom-law-nm", dest="prom_law_nm", default=None)
    p.add_argument("--prom-no", dest="prom_no", default=None)
    p.add_argument("--promulgation-dt", dest="promulgation_dt", default=None)

    p = sub.add_parser("load-institutional-system", help="명시적 다법령 제도 묶음 로딩.")
    p.add_argument("--statute", dest="statute", action="append", default=[], help="law_id. 반복 지정. (예: --statute 001248 --statute 001250)")
    _add_articles(p); _add_budget(p); _add_as_of(p)

    p = sub.add_parser("load-delegated-criteria", help="법령 앵커에서 위임 집행기준 로딩.")
    _add_law(p); _add_articles(p); p.add_argument("--query", default=None)
    _add_budget(p); _add_as_of(p)

    p = sub.add_parser("load-followup", help="bundle/expand가 준 deferred를 본문으로 실행. --json '<객체>' 또는 --json - (stdin/파이프).")
    p.add_argument("--json", dest="json_arg", required=True, help="deferred 객체 JSON, 또는 '-'로 stdin. 손타이핑 대신 data.deferred[i]를 파이프하라.")

    return parser

__all__ = [name for name in globals() if not name.startswith("__")]
