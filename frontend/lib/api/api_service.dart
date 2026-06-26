import 'dart:convert';

import 'package:http/http.dart' as http;

/// Simple API client for the FastAPI backend.
class ApiService {
  // Backend base URL (run uvicorn from the backend/ folder).
  static const String baseUrl = 'http://127.0.0.1:8000';

  /// Fetch the top 100 cryptocurrencies by market cap.
  /// GET /top100
  static Future<List<dynamic>> getCoins() async {
    final response = await http.get(Uri.parse('$baseUrl/top100'));

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as List<dynamic>;
    }

    throw Exception('Failed to load coins: ${response.statusCode}');
  }

  /// Fetch the current live price for one coin.
  /// GET /coin/{coinId}/live
  static Future<Map<String, dynamic>> getLivePrice(String coinId) async {
    final response = await http.get(Uri.parse('$baseUrl/coin/$coinId/live'));

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }

    throw Exception('Failed to load live price: ${response.statusCode}');
  }

  /// Fetch historical price data for one coin.
  /// GET /coin/{coinId}/history?days={days}
  static Future<List<dynamic>> getHistory(String coinId, int days) async {
    final uri = Uri.parse('$baseUrl/coin/$coinId/history?days=$days');
    final response = await http.get(uri);

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as List<dynamic>;
    }

    throw Exception('Failed to load history: ${response.statusCode}');
  }

  /// Fetch ML price predictions for one coin.
  /// GET /predict/{coinId}?days={days}&model={model}
  static Future<Map<String, dynamic>> getPrediction(
    String coinId,
    int days, {
    String model = 'random_forest',
  }) async {
    final uri = Uri.parse(
      '$baseUrl/predict/$coinId?days=$days&model=$model',
    );
    final response = await http.get(uri);

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }

    throw Exception('Failed to load prediction: ${response.statusCode}');
  }

  /// Fetch ML training metrics for one coin (best model, RMSE, etc.).
  /// GET /metrics/{coinId}
  static Future<Map<String, dynamic>> getMetrics(String coinId) async {
    final response = await http.get(Uri.parse('$baseUrl/metrics/$coinId'));

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }

    throw Exception('Failed to load metrics: ${response.statusCode}');
  }
}
