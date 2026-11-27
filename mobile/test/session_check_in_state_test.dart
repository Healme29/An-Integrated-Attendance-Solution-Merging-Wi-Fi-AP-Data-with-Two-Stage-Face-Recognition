import 'package:flutter_test/flutter_test.dart';
import 'package:zhen_dao/models/student.dart';

void main() {
  group('SessionCheckInState.fromHistory', () {
    test('empty history records nothing', () {
      final state = SessionCheckInState.fromHistory(const [], 12);
      expect(state.startDone, isFalse);
      expect(state.endDone, isFalse);
      expect(state.spotRounds, isEmpty);
      expect(state.startTime, isNull);
      expect(state.endTime, isNull);
    });

    test('ignores rows from other sessions', () {
      final state = SessionCheckInState.fromHistory(const [
        {'qr_session_id': 11, 'check_type': 'start', 'timestamp': '2026-11-27 09:00:00'},
        {'qr_session_id': 12, 'check_type': 'start', 'timestamp': '2026-11-27 10:00:00'},
      ], 12);
      expect(state.startDone, isTrue);
      expect(state.startTime, '2026-11-27 10:00:00');
    });

    test('reads start, end and spot rows for the target session', () {
      final state = SessionCheckInState.fromHistory(const [
        {'qr_session_id': 12, 'check_type': 'start', 'timestamp': '2026-11-27 10:00:00'},
        {'qr_session_id': 12, 'check_type': 'spot', 'spot_round': 1, 'timestamp': '2026-11-27 10:20:00'},
        {'qr_session_id': 12, 'check_type': 'spot', 'spot_round': 2, 'timestamp': '2026-11-27 10:40:00'},
        {'qr_session_id': 12, 'check_type': 'end', 'timestamp': '2026-11-27 11:00:00'},
      ], 12);
      expect(state.startDone, isTrue);
      expect(state.endDone, isTrue);
      expect(state.spotRounds, {1, 2});
      expect(state.spotDone(1), isTrue);
      expect(state.spotDone(2), isTrue);
      expect(state.spotDone(3), isFalse);
      expect(state.endTime, '2026-11-27 11:00:00');
    });

    test('tolerates rows with a missing check_type as start', () {
      final state = SessionCheckInState.fromHistory(const [
        {'qr_session_id': 12, 'timestamp': '2026-11-27 10:00:00'},
      ], 12);
      expect(state.startDone, isTrue);
    });
  });
}
