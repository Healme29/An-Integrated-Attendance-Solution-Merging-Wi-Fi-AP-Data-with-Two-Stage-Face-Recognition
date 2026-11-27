import 'package:flutter_test/flutter_test.dart';

import 'package:zhen_dao/main.dart';

void main() {
  testWidgets('App builds and shows login when no session', (WidgetTester tester) async {
    await tester.pumpWidget(const FaceAttendanceApp());

    expect(find.text('真到'), findsOneWidget);
  });
}
