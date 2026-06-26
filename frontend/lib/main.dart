import 'package:flutter/material.dart';

import 'screens/dashboard.dart';

void main() {
  runApp(const CryptoForecastingApp());
}

/// Root app widget with dark theme dashboard.
class CryptoForecastingApp extends StatelessWidget {
  const CryptoForecastingApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Crypto Forecasting',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF0F1117),
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF6C8CFF),
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
      ),
      home: const DashboardScreen(),
    );
  }
}
