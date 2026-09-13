from mping.models import PingOutcome, PingTarget


def test_record_success_updates_counts_and_rtt():
    target = PingTarget(destination="1.1.1.1", display_name="1.1.1.1")
    target.record_success(0.012)
    assert target.success_count == 1
    assert target.fail_count == 0
    assert target.expired_count == 0
    assert target.last_rtt == 0.012
    assert target.total_count == 1


def test_record_fail_and_expired_are_counted_separately():
    target = PingTarget(destination="1.1.1.1", display_name="1.1.1.1")
    target.record_fail()
    target.record_expired(0.5)
    assert target.fail_count == 1
    assert target.expired_count == 1
    assert target.success_count == 0
    assert target.total_count == 2


def test_blink_alternates_every_packet_regardless_of_outcome():
    target = PingTarget(destination="1.1.1.1", display_name="1.1.1.1")
    target.record_success(0.01)
    target.record_success(0.01)
    target.record_fail()
    blinks = [entry.blink for entry in target.history]
    assert blinks == [False, True, False]


def test_history_outcomes_recorded_in_order():
    target = PingTarget(destination="1.1.1.1", display_name="1.1.1.1")
    target.record_success(0.01)
    target.record_fail()
    target.record_expired(0.2)
    outcomes = [entry.outcome for entry in target.history]
    assert outcomes == [PingOutcome.SUCCESS, PingOutcome.FAIL, PingOutcome.EXPIRED]


def test_history_respects_maxlen():
    target = PingTarget(destination="1.1.1.1", display_name="1.1.1.1", history_size=3)
    for _ in range(5):
        target.record_success(0.01)
    assert len(target.history) == 3
    # 直近3件のみ残る = 成功回数のカウント自体は減らない
    assert target.success_count == 5
