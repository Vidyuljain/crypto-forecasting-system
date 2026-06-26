import 'dart:async';

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../api/api_service.dart';

/// Main crypto forecasting dashboard screen.
class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  // Dark theme colors.
  static const Color background = Color(0xFF0F1117);
  static const Color cardColor = Color(0xFF1A1D26);
  static const Color accent = Color(0xFF6C8CFF);
  static const Color actualColor = Color(0xFF4ADE80);
  static const Color predictedColor = Color(0xFFF59E0B);

  List<dynamic> _coins = [];
  String? _selectedCoinId;
  String _selectedCoinName = '';

  Map<String, dynamic>? _livePrice;
  List<dynamic> _history = [];
  List<dynamic> _predictions = [];
  Map<String, dynamic>? _metrics;

  int _historyDays = 30;
  int _predictionDays = 7;
  String _selectedModel = 'random_forest';

  bool _loading = true;
  String? _error;

  Timer? _livePriceTimer;

  final NumberFormat _priceFormat = NumberFormat.currency(symbol: '\$', decimalDigits: 2);

  @override
  void initState() {
    super.initState();
    _loadCoins();
  }

  @override
  void dispose() {
    _livePriceTimer?.cancel();
    super.dispose();
  }

  /// Poll live price every 10 seconds without reloading the whole dashboard.
  void _startLivePriceTimer() {
    _livePriceTimer?.cancel();
    _livePriceTimer = Timer.periodic(const Duration(seconds: 10), (_) {
      _refreshLivePrice();
    });
  }

  /// Fetch only the live price and update the price card.
  Future<void> _refreshLivePrice() async {
    if (_selectedCoinId == null || !mounted) return;

    try {
      final live = await ApiService.getLivePrice(_selectedCoinId!);
      if (!mounted) return;

      setState(() {
        _livePrice = live;
      });
    } catch (_) {
      // Keep showing the last known price if a poll fails.
    }
  }

  /// Load coin list from backend.
  Future<void> _loadCoins() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final coins = await ApiService.getCoins();
      if (coins.isEmpty) {
        throw Exception('No coins returned from API');
      }

      final firstCoin = coins.first as Map<String, dynamic>;
      setState(() {
        _coins = coins;
        _selectedCoinId = firstCoin['id'] as String;
        _selectedCoinName = firstCoin['name'] as String? ?? _selectedCoinId!;
      });

      await _loadDashboardData();
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  /// Refresh live price, history, predictions, and metrics.
  Future<void> _loadDashboardData() async {
    if (_selectedCoinId == null) return;

    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final live = await ApiService.getLivePrice(_selectedCoinId!);
      final history = await ApiService.getHistory(_selectedCoinId!, _historyDays);
      final prediction = await ApiService.getPrediction(
        _selectedCoinId!,
        _predictionDays,
        model: _selectedModel,
      );

      Map<String, dynamic>? metrics;
      try {
        metrics = await ApiService.getMetrics(_selectedCoinId!);
      } catch (_) {
        metrics = null;
      }

      setState(() {
        _livePrice = live;
        _history = history;
        _predictions = prediction['predictions'] as List<dynamic>? ?? [];
        _metrics = metrics;
        _loading = false;
      });

      _startLivePriceTimer();
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  void _onCoinChanged(String? coinId) {
    if (coinId == null) return;

    final coin = _coins.firstWhere(
      (item) => (item as Map<String, dynamic>)['id'] == coinId,
    ) as Map<String, dynamic>;

    setState(() {
      _selectedCoinId = coinId;
      _selectedCoinName = coin['name'] as String? ?? coinId;
    });

    _loadDashboardData();
  }

  void _onHistoryDaysChanged(int days) {
    setState(() => _historyDays = days);
    _loadDashboardData();
  }

  void _onModelChanged(String? model) {
    if (model == null) return;
    setState(() => _selectedModel = model);
    _loadDashboardData();
  }

  String _bestModelLabel() {
    final best = _metrics?['best_model'] as String?;
    if (best == 'linear_regression') return 'Linear Regression';
    if (best == 'random_forest') return 'Random Forest';
    return 'Unknown';
  }

  List<FlSpot> _historySpots() {
    return List.generate(_history.length, (index) {
      final item = _history[index] as Map<String, dynamic>;
      final price = (item['price'] as num).toDouble();
      return FlSpot(index.toDouble(), price);
    });
  }

  /// Build actual vs predicted chart using recent history + forecast.
  List<LineChartBarData> _comparisonBars() {
    final actualSpots = _historySpots();
    if (actualSpots.isEmpty || _predictions.isEmpty) return [];

    final startIndex = actualSpots.length.toDouble();
    final predictedSpots = List.generate(_predictions.length, (index) {
      final item = _predictions[index] as Map<String, dynamic>;
      final price = (item['predicted_price'] as num).toDouble();
      return FlSpot(startIndex + index.toDouble(), price);
    });

    // Connect last actual point to first predicted point for continuity.
    final bridgeSpots = [
      actualSpots.last,
      predictedSpots.first,
    ];

    return [
      LineChartBarData(
        spots: actualSpots,
        isCurved: true,
        color: actualColor,
        barWidth: 3,
        dotData: const FlDotData(show: false),
      ),
      LineChartBarData(
        spots: bridgeSpots,
        isCurved: false,
        color: predictedColor.withOpacity(0.5),
        barWidth: 2,
        dashArray: [6, 4],
        dotData: const FlDotData(show: false),
      ),
      LineChartBarData(
        spots: predictedSpots,
        isCurved: true,
        color: predictedColor,
        barWidth: 3,
        dashArray: [8, 4],
        dotData: const FlDotData(show: true),
      ),
    ];
  }

  Widget _periodButton(String label, int days) {
    final selected = _historyDays == days;

    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: ChoiceChip(
        label: Text(label),
        selected: selected,
        onSelected: (_) => _onHistoryDaysChanged(days),
        selectedColor: accent,
        backgroundColor: cardColor,
        labelStyle: TextStyle(
          color: selected ? Colors.white : Colors.white70,
        ),
      ),
    );
  }

  Widget _priceCard() {
    final price = (_livePrice?['price'] as num?)?.toDouble();
    final timestamp = _livePrice?['timestamp'] as String? ?? '';

    return Card(
      color: cardColor,
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _selectedCoinName,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  price != null ? _priceFormat.format(price) : '--',
                  style: const TextStyle(
                    color: accent,
                    fontSize: 28,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                const Text('Live Price', style: TextStyle(color: Colors.white54)),
                const SizedBox(height: 8),
                Text(timestamp, style: const TextStyle(color: Colors.white70)),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _chartCard({
    required String title,
    required Widget chart,
    String? subtitle,
  }) {
    return Card(
      color: cardColor,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            if (subtitle != null) ...[
              const SizedBox(height: 4),
              Text(subtitle, style: const TextStyle(color: Colors.white54)),
            ],
            const SizedBox(height: 16),
            SizedBox(height: 260, child: chart),
          ],
        ),
      ),
    );
  }

  Widget _historyChart() {
    final spots = _historySpots();
    if (spots.isEmpty) {
      return const Center(child: Text('No history data', style: TextStyle(color: Colors.white54)));
    }

    return LineChart(
      LineChartData(
        gridData: FlGridData(show: true, drawVerticalLine: false, getDrawingHorizontalLine: (v) {
          return FlLine(color: Colors.white12, strokeWidth: 1);
        }),
        titlesData: const FlTitlesData(show: false),
        borderData: FlBorderData(show: false),
        lineBarsData: [
          LineChartBarData(
            spots: spots,
            isCurved: true,
            color: accent,
            barWidth: 3,
            belowBarData: BarAreaData(
              show: true,
              color: accent.withOpacity(0.15),
            ),
            dotData: const FlDotData(show: false),
          ),
        ],
      ),
    );
  }

  Widget _comparisonChart() {
    final bars = _comparisonBars();
    if (bars.isEmpty) {
      return const Center(
        child: Text('No comparison data', style: TextStyle(color: Colors.white54)),
      );
    }

    return LineChart(
      LineChartData(
        gridData: FlGridData(show: true, drawVerticalLine: false, getDrawingHorizontalLine: (v) {
          return FlLine(color: Colors.white12, strokeWidth: 1);
        }),
        titlesData: const FlTitlesData(show: false),
        borderData: FlBorderData(show: false),
        lineBarsData: bars,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: background,
      appBar: AppBar(
        backgroundColor: cardColor,
        title: const Text('Crypto Forecasting Dashboard'),
        actions: [
          IconButton(
            onPressed: _loadDashboardData,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: accent))
          : _error != null
              ? Center(
                  child: Text(_error!, style: const TextStyle(color: Colors.redAccent)),
                )
              : SingleChildScrollView(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Coin selector dropdown.
                      Card(
                        color: cardColor,
                        child: Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                          child: DropdownButton<String>(
                            isExpanded: true,
                            dropdownColor: cardColor,
                            value: _selectedCoinId,
                            underline: const SizedBox(),
                            items: _coins.map((coin) {
                              final item = coin as Map<String, dynamic>;
                              final id = item['id'] as String;
                              final name = item['name'] as String? ?? id;
                              return DropdownMenuItem(
                                value: id,
                                child: Text(name, style: const TextStyle(color: Colors.white)),
                              );
                            }).toList(),
                            onChanged: _onCoinChanged,
                          ),
                        ),
                      ),
                      const SizedBox(height: 16),

                      _priceCard(),
                      const SizedBox(height: 16),

                      // History period buttons.
                      SingleChildScrollView(
                        scrollDirection: Axis.horizontal,
                        child: Row(
                          children: [
                            _periodButton('7 days', 7),
                            _periodButton('30 days', 30),
                            _periodButton('6 months', 180),
                            _periodButton('1 year', 365),
                            _periodButton('All', 1825),
                          ],
                        ),
                      ),
                      const SizedBox(height: 16),

                      _chartCard(
                        title: 'Historical Price',
                        subtitle: 'Last $_historyDays days',
                        chart: _historyChart(),
                      ),
                      const SizedBox(height: 16),

                      // Prediction model selector + best model badge.
                      Card(
                        color: cardColor,
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text(
                                'Prediction Model',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 18,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                              const SizedBox(height: 12),
                              DropdownButton<String>(
                                isExpanded: true,
                                dropdownColor: cardColor,
                                value: _selectedModel,
                                underline: const SizedBox(),
                                items: const [
                                  DropdownMenuItem(
                                    value: 'linear_regression',
                                    child: Text('Linear Regression', style: TextStyle(color: Colors.white)),
                                  ),
                                  DropdownMenuItem(
                                    value: 'random_forest',
                                    child: Text('Random Forest', style: TextStyle(color: Colors.white)),
                                  ),
                                ],
                                onChanged: _onModelChanged,
                              ),
                              const SizedBox(height: 12),
                              Container(
                                width: double.infinity,
                                padding: const EdgeInsets.all(12),
                                decoration: BoxDecoration(
                                  color: background,
                                  borderRadius: BorderRadius.circular(8),
                                ),
                                child: Text(
                                  'Best model (from metrics): ${_bestModelLabel()}',
                                  style: const TextStyle(color: Colors.white70),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 16),

                      _chartCard(
                        title: 'Actual vs Predicted',
                        subtitle: 'Green = actual history, Orange = $_predictionDays-day forecast',
                        chart: _comparisonChart(),
                      ),
                    ],
                  ),
                ),
    );
  }
}
