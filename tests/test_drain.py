"""Drain parser checks, using the examples of He et al. (ICWS 2017) Figures 2-3."""

from __future__ import annotations

import pytest

from src.shared.domain.canonical import LogEvent
from src.shared.infrastructure.drain import (
    WILDCARD,
    DrainConfig,
    DrainParser,
    assign_drain_templates,
    sim_seq,
    split_header,
)


def event(log_id: str, parsed: str, incident: str = "inc1") -> LogEvent:
    return LogEvent(
        log_id=log_id, incident_id=incident, raw_message=parsed, source_file="f",
        source_row_id=log_id, raw_record_ref=f"f#row_{log_id}", parsed_message=parsed,
    )


def test_sim_seq_counts_equal_positions_over_message_length():
    assert sim_seq(["Receive", "from", "node", "4"], ["Receive", "from", "node", "5"]) == pytest.approx(0.75)


def test_figure2_same_event_merges_and_wildcards_the_variable():
    parser = DrainParser(DrainConfig(depth=3, st=0.4))
    first = parser.add("1", "Receive from node 4".split())
    second = parser.add("23", "Receive from node 5".split())
    assert first is second
    assert first.template_text == f"Receive from node {WILDCARD}"
    assert first.log_ids == ["1", "23"]


def test_figure3_token_with_digits_goes_to_wildcard_node():
    parser = DrainParser(DrainConfig(depth=4, st=0.4))
    parser.add("1", "Send block 44".split())
    parser.add("2", "Receive 120 bytes".split())
    length_node = parser.length_layer[3]
    assert set(length_node.children) == {"Send", "Receive"}
    assert set(length_node.children["Send"].children) == {"block"}
    assert set(length_node.children["Receive"].children) == {WILDCARD}
    assert len(parser.groups) == 2


def test_different_lengths_never_share_a_group():
    parser = DrainParser(DrainConfig(depth=3, st=0.0))
    assert parser.add("1", "a b".split()) is not parser.add("2", "a b c".split())


def test_similarity_threshold_decides_merge():
    # depth 2: only the length layer, so both messages reach the same leaf.
    strict = DrainParser(DrainConfig(depth=2, st=0.5))
    assert strict.add("1", "a b c d".split()) is not strict.add("2", "a x y z".split())
    loose = DrainParser(DrainConfig(depth=2, st=0.25))
    assert loose.add("1", "a b c d".split()) is loose.add("2", "a x y z".split())


def test_full_node_sends_new_tokens_to_wildcard_child():
    parser = DrainParser(DrainConfig(depth=3, st=0.4, max_child=1))
    parser.add("1", "alpha x".split())
    parser.add("2", "beta x".split())
    assert set(parser.length_layer[2].children) == {"alpha", WILDCARD}


def test_every_log_id_lands_in_exactly_one_group():
    parser = DrainParser(DrainConfig())
    messages = ["a b c", "a b d", "x y z", "a b c", "q", "x y w", "a"]
    for number, message in enumerate(messages):
        parser.add(str(number), message.split())
    members = [log_id for group in parser.groups for log_id in group.log_ids]
    assert sorted(members) == sorted(str(n) for n in range(len(messages)))


def test_config_rejects_invalid_values():
    with pytest.raises(ValueError):
        DrainConfig(depth=1)
    with pytest.raises(ValueError):
        DrainConfig(st=1.5)
    with pytest.raises(ValueError):
        DrainConfig(max_child=0)


def test_split_header_nezha_formats():
    tt = "<N>:<N>:<N> WARN  o.s.OrderOtherServiceImpl#<N> TraceID: <HEX> SpanID: <HEX> [getSoldTickets][Seat]"
    assert split_header(tt) == ("WARN o.s.OrderOtherServiceImpl#<N>", ["[getSoldTickets][Seat]"])
    ob = "TraceID: <HEX> SpanID: <HEX> Get currency data successful"
    assert split_header(ob) == ("", ["Get", "currency", "data", "successful"])


def test_split_header_spring_boot_and_go_kit():
    spring = "INFO <N> --- [io-<N>-exec-<N>] route.controller.RouteController    : Route id: <UUID>"
    assert split_header(spring) == ("INFO route.controller.RouteController :", ["Route", "id:", "<UUID>"])
    sleuth = "WARN [orders,<HEX>,<HEX>,false] <N> --- <THREAD> w.w.s.o.OrdersController : Payment failed"
    assert split_header(sleuth) == ("WARN w.w.s.o.OrdersController :", ["Payment", "failed"])
    go_kit = "ts=<N>-<N>-18T16:<N>:<N>.623814152Z caller=logging.go:<N> method=Health"
    assert split_header(go_kit) == ("", ["caller=logging.go:<N>", "method=Health"])
    assert split_header("request started") == ("", ["request", "started"])


def test_every_member_gets_the_final_template_of_its_group():
    events = [event("1", "Receive from node 4"), event("2", "Receive from node 5"), event("3", "")]
    out = assign_drain_templates(events, DrainConfig(depth=3))
    assert out[0].drain_template == out[1].drain_template == f"Receive from node {WILDCARD}"
    assert out[0].drain_template_id == out[1].drain_template_id
    assert out[2].drain_template is None and out[2].drain_template_id is None
    # Everything else, including the regex template, is untouched.
    assert [e.log_id for e in out] == ["1", "2", "3"]
    assert out[0].parsed_message == "Receive from node 4"


def test_each_incident_gets_its_own_tree():
    events = [
        event("a1", "Receive from node 4", "incA"),
        event("a2", "Receive from node 5", "incA"),
        event("b1", "Receive from node 4", "incB"),
    ]
    out = assign_drain_templates(events, DrainConfig(depth=3))
    assert out[0].drain_template == f"Receive from node {WILDCARD}"
    assert out[2].drain_template == "Receive from node 4"


def test_header_is_kept_as_prefix_and_loggers_never_merge():
    events = [
        event("1", "INFO <N> --- [main] a.Foo : Order created"),
        event("2", "INFO <N> --- [main] a.Bar : Order created"),
        event("3", "INFO <N> --- [main] a.Foo : Order updated"),
    ]
    out = assign_drain_templates(events, DrainConfig(depth=2, st=0.4))
    assert out[0].drain_template == f"INFO a.Foo : Order {WILDCARD}"
    assert out[2].drain_template == out[0].drain_template
    assert out[1].drain_template == "INFO a.Bar : Order created"
