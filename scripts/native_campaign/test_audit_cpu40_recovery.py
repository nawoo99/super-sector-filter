from audit_cpu40_recovery import audit_text


def line(timestamp, payload):
    return f'[node-2] [INFO] [{timestamp}] [test]: {payload}'


def source(frame=2, cycle=1, full=1, stamp=1100000000, angle='45.000'):
    width = 900 if full else 225
    return line('9.0', f'[SENSOR_ACQUISITION_FRAME] frame={frame} cycle={cycle} '
                f'full={full} stamp_ns={stamp} width={width} height=445 '
                f'readback_pixels={2*width*445} conversion_rays={128*width} '
                f'generated_points=3 bytes=96 half_angle_deg={angle}')


def episode():
    return [
        source(frame=1, cycle=0, full=0, stamp=900000000),
        line('1.0', '[EVENT_RECOVERY_FULL] cycle=1 input_boundary=1'),
        source(),
        line('1.2', '[EVENT_RECOVERY_MAP_ACK] cycle=1 stamp_ns=1100000000 map=5'),
        line('1.3', '[EVENT_RECOVERY_PATH_READY] request_seq=7 stamp_ns=1100000000 '
             'ack_map=5 certified_map=6 generation_before=3 generation_after=4'),
        line('1.4', '[EVENT_RECOVERY_SECTOR] cycle=1 stamp_ns=1100000000 '
             'map=5 committed=1 planner_release=1'),
    ]


def audited(lines):
    return audit_text('\n'.join(lines))


def codes(result):
    return {item['code'] for item in result['errors']}


def test_valid_cycle_and_buffered_source_line_order():
    lines = episode()
    result = audited([lines[5], lines[3], lines[1], lines[4], lines[2], lines[0]])
    assert result['valid']
    assert len(result['completed_cycles']) == 1
    assert result['completed_cycles'][0]['source_frame'] == 2
    assert result['timestamp_observed_completed_cycles'] == 1


def test_non_45_angle_rejected_in_any_source_record():
    for index in (0, 2):
        lines = episode()
        lines[index] = lines[index].replace('45.000', '44.000')
        assert 'source_angle_not_45' in codes(audited(lines))
    lines = episode()
    lines[2] = lines[2].replace('45.000', 'nan')
    assert not audited(lines)['valid']


def test_missing_certificate_and_duplicate_certificate_rejected():
    lines = episode()
    assert not audited(lines[:4] + lines[5:])['valid']
    assert not audited(lines + [lines[4]])['valid']


def test_wrong_source_cycle_and_non_full_source_rejected():
    for replacement in (source(cycle=2), source(full=0)):
        lines = episode()
        lines[2] = replacement
        assert 'stale_or_wrong_cycle_source' in codes(audited(lines))


def test_source_frame_must_follow_input_boundary():
    lines = episode()
    lines[1] = lines[1].replace('input_boundary=1', 'input_boundary=2')
    assert 'stale_or_wrong_cycle_source' in codes(audited(lines))


def test_old_source_stamp_rejected_even_with_correct_cycle_and_frame():
    lines = [item.replace('1100000000', '950000000') for item in episode()]
    assert 'source_before_full_open' in codes(audited(lines))


def test_wrong_ack_map_or_cycle_rejected():
    for before, after in (('map=5', 'map=4'), ('cycle=1', 'cycle=2')):
        lines = episode()
        lines[3] = lines[3].replace(before, after)
        assert not audited(lines)['valid']


def test_generation_and_committed_release_required():
    for index, before, after in (
            (4, 'generation_after=4', 'generation_after=3'),
            (4, 'certified_map=6', 'certified_map=4'),
            (5, 'committed=1', 'committed=0'),
            (5, 'planner_release=1', 'planner_release=0')):
        lines = episode()
        lines[index] = lines[index].replace(before, after)
        assert not audited(lines)['valid']


def test_reversed_ack_path_and_path_sector_times_rejected():
    lines = episode()
    lines[4] = lines[4].replace('[1.3]', '[1.15]')
    assert 'path_before_committed_ack' in codes(audited(lines))
    lines = episode()
    lines[5] = lines[5].replace('[1.4]', '[1.25]')
    assert 'sector_before_path' in codes(audited(lines))


def test_exact_fsm_ack_permits_delayed_frontend_ack_delivery():
    lines = episode()
    lines[3] = lines[3].replace('[1.2]', '[1.35]')
    lines.append(line('1.2', '[FULL_REFRESH_RECOVERY_ACK] request_seq=7 '
                      'stamp_ns=1100000000 map=5 committed=1'))
    assert audited(lines)['valid']
    lines[-1] = lines[-1].replace('request_seq=7', 'request_seq=8')
    assert not audited(lines)['valid']


def test_decimal_timestamp_order_does_not_round_away_nanoseconds():
    lines = episode()
    lines[4] = lines[4].replace('[1.3]', '[1789500000.123456789]')
    lines[5] = lines[5].replace('[1.4]', '[1789500000.123456788]')
    assert 'sector_before_path' in codes(audited(lines))


def test_outstanding_cycle_reported_not_completed_or_invalid_closed():
    lines = episode()[:4]
    result = audited(lines)
    assert result['valid']
    assert result['outstanding_cycles'] == [1]
    assert result['completed_cycles'] == []
    assert not audit_text('\n'.join(lines), require_all_closed=True)['valid']


def test_duplicate_closure_or_missing_open_rejected():
    lines = episode()
    assert not audited(lines + [lines[-1]])['valid']
    assert not audited([lines[0], *lines[2:]])['valid']


def test_empty_malformed_and_duplicate_source_records_rejected():
    assert not audit_text('')['valid']
    lines = episode()
    assert not audited(lines + [lines[2]])['valid']
    lines[2] = '[SENSOR_ACQUISITION_FRAME] broken'
    assert not audited(lines)['valid']


def test_full_control_supported_and_sector_never_full():
    assert audit_text(source(frame=1, cycle=0), mode='full')['valid']
    assert not audit_text(source(frame=1, cycle=0), mode='sector')['valid']
