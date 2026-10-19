"""Session slots (TD-336, TD-105): the machine's total and each project's limit, round-robin, first-ready."""

from owlbear_delivery_next.local_system.slots import PACK, Slots


def test_the_machine_total_and_each_project_s_limit_hold_together():
    total = [3]
    s = Slots(lambda: total[0])
    assert (s.take("a", "c1", 1, 2), s.take("a", "c2", 1, 2), s.take("a", "c3", 1, 2)) == (1, 1, 0)  # a's limit
    assert s.take("b", "d1", 4, 4) == 1  # the machine's last slot
    assert s.take("b", "d2", 1, 4) == 0
    assert s.counts("a") == (3, 3, 2)
    total[0] = 1  # lowered: nothing that runs is stopped
    s.give("a", "c1")
    assert (s.take("a", "c3", 1, 2), s.counts("b")) == (0, (2, 1, 1))  # still over the new total
    assert s.take("a", "c1", 1, 2) == 0


def test_a_free_slot_goes_round_robin_across_projects_and_first_ready_within_one():
    s, woken = Slots(lambda: 1), []
    for p in ("a", "b", "c"):
        s.waker(p, lambda p=p: woken.append(p))
    assert s.take("a", "a1", 1, 2) == 1
    assert [s.take(p, k, 1, 2) for p, k in (("a", "a2"), ("c", "c1"), ("b", "b1"), ("a", "a3"))] == [0, 0, 0, 0]
    s.give("a", "a1")
    assert woken[-1] == "b"  # the next project after a, not a again
    assert (s.take("c", "c1", 1, 2), s.take("a", "a3", 1, 2), s.take("b", "b1", 1, 2)) == (0, 0, 1)
    s.give("b", "b1")
    assert (s.take("a", "a3", 1, 2), s.take("c", "c1", 1, 2)) == (0, 1)  # c after b
    s.give("c", "c1")
    assert (s.take("a", "a3", 1, 2), s.take("a", "a2", 1, 2)) == (0, 1)  # a's first-ready: a2 waited longest


def test_a_project_at_its_limit_never_blocks_another_and_a_held_key_keeps_its_grant():
    s = Slots(lambda: 4)
    assert (s.take("a", "a1", 2, 2), s.take("a", "a2", 1, 2)) == (2, 0)  # a is full; a2 waits
    assert s.take("b", "b1", 3, 2) == 2  # capped by b's limit, though a2 waits first
    assert s.take("a", "a1", 2, 2) == 2  # asked again while it holds


def test_a_reservation_rebuilt_after_a_restart_counts_before_anything_is_granted():
    s = Slots(lambda: 2, closed=True)
    assert s.take("a", "a1", 1, 2) == 0  # closed until every project's runners are known
    s.restore("b", {"b1": 2, "b2": 0})
    s.open()
    assert s.take("a", "a1", 1, 2) == 0
    s.restore("b", {})  # b loads again and finds its runner gone
    assert s.take("a", "a1", 1, 2) == 1


def test_a_stopped_project_waits_for_nothing_and_its_turn_goes_on():
    s, woken = Slots(lambda: 1), []
    for p in ("a", "b", "c"):
        s.waker(p, lambda p=p: woken.append(p))
    assert s.take("a", "a1", 1, 1) == 1
    assert (s.take("b", "b1", 1, 1), s.take("c", "c1", 1, 1)) == (0, 0)
    s.give("a", "a1")
    assert woken[-1] == "b"
    s.leave("b")  # b stops before it takes its turn
    assert (woken[-1], s.take("c", "c1", 1, 1)) == ("c", 1)


def test_a_waiter_with_its_own_wake_is_woken_itself_and_a_slot_left_free_goes_on():
    s, woken = Slots(lambda: 2), []
    s.waker("a", lambda: woken.append("host a"))
    s.waker("b", lambda: woken.append("host b"))
    assert s.take("a", "a1", 2, 2) == 2
    assert s.take("b", f"{PACK}x", 1, 2, lambda: woken.append("pack")) == 0
    assert s.take("a", "a2", 1, 2) == 0
    s.give("a", "a1")
    assert woken[-1] == "pack"  # its turn wakes the update's thread, not its project's host
    assert s.take("b", f"{PACK}x", 1, 2) == 1
    assert woken[-1] == "host a"  # the other free slot goes on to a
    s.give("b", f"{PACK}x")
    s.give("b", f"{PACK}never")  # a wait that ended without a slot is harmless
    assert s.counts("b") == (0, 2, 0)


def test_changes_no_longer_ready_stop_waiting_but_a_pack_update_keeps_its_place():
    s = Slots(lambda: 1)
    assert s.take("a", "a0", 1, 1) == 1
    assert (s.take("b", "b1", 1, 1), s.take("b", f"{PACK}run", 1, 1), s.take("c", "c1", 1, 1)) == (0, 0, 0)
    s.keep("b", set())  # b1 is paused now
    s.give("a", "a0")
    assert (s.take("c", "c1", 1, 1), s.take("b", f"{PACK}run", 1, 1)) == (0, 1)  # b's pack session kept its turn


def test_forgetting_a_change_that_held_the_turn_wakes_the_next():
    s, woken = Slots(lambda: 1), []
    s.waker("c", lambda: woken.append("c"))
    assert s.take("a", "a0", 1, 1) == 1
    assert (s.take("b", "b1", 1, 1), s.take("c", "c1", 1, 1)) == (0, 0)
    s.give("a", "a0")
    s.keep("b", set())
    assert woken == ["c"]
