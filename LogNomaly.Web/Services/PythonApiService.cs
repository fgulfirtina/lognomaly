using System.Text;
using System.Text.Json;
using LogNomaly.Web.Entities.Models;
using LogNomaly.Web.Services.Contracts;

namespace LogNomaly.Web.Services
{

    public class PythonApiService : IPythonApiService
    {
        private readonly HttpClient _http;
        private readonly ILogger<PythonApiService> _logger;

        private static readonly JsonSerializerOptions _json = new()
        {
            PropertyNameCaseInsensitive = true,
            PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower
        };

        public PythonApiService(HttpClient http, ILogger<PythonApiService> logger)
        {
            _http = http;
            _logger = logger;
        }

        public async Task<HealthResponse?> GetHealthAsync()
        {
            try
            {
                var resp = await _http.GetAsync("/api/health");
                return await resp.Content.ReadFromJsonAsync<HealthResponse>(_json);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Health check error");
                return null;
            }
        }

        public async Task<UploadResponse?> UploadFileAsync(IFormFile file)
        {
            try
            {
                using var form = new MultipartFormDataContent();
                using var stream = file.OpenReadStream();
                form.Add(new StreamContent(stream), "file", file.FileName);

                var resp = await _http.PostAsync("/api/upload", form);
                if (!resp.IsSuccessStatusCode)
                {
                    _logger.LogWarning("Upload failed: {Status}", resp.StatusCode);
                    return null;
                }
                return await resp.Content.ReadFromJsonAsync<UploadResponse>(_json);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "File upload error");
                return null;
            }
        }

        public async Task<AnalyzeResponse?> AnalyzeFileAsync(string filePath, string sessionId)
        {
            try
            {
                var payload = new { file_path = filePath, session_id = sessionId };
                var content = new StringContent(JsonSerializer.Serialize(payload), Encoding.UTF8, "application/json");

                var resp = await _http.PostAsync("/api/analyze", content);
                if (!resp.IsSuccessStatusCode)
                {
                    _logger.LogWarning("Analysis failed: {Status}", resp.StatusCode);
                    return null;
                }
                return await resp.Content.ReadFromJsonAsync<AnalyzeResponse>(_json);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "File analyze error");
                return null;
            }
        }

        public async Task<AnalysisResult?> AnalyzeSingleAsync(string logLine, string level = "INFO")
        {
            try
            {
                var payload = new { log = logLine, level };
                var content = new StringContent(JsonSerializer.Serialize(payload), Encoding.UTF8, "application/json");

                var resp = await _http.PostAsync("/api/analyze/single", content);
                if (!resp.IsSuccessStatusCode) return null;
                return await resp.Content.ReadFromJsonAsync<AnalysisResult>(_json);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Single line analyze error");
                return null;
            }
        }

        public async Task<AnalysisStats?> GetStatsAsync(string sessionId)
        {
            try
            {
                var resp = await _http.GetAsync($"/api/stats/{sessionId}");
                return await resp.Content.ReadFromJsonAsync<AnalysisStats>(_json);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Stats error");
                return null;
            }
        }

        public async Task<AnalyzeResponse?> GetResultsAsync(string sessionId, int page = 1, int limit = 100)
        {
            try
            {
                var resp = await _http.GetAsync($"/api/results/{sessionId}?page={page}&limit={limit}");
                if (!resp.IsSuccessStatusCode) return null;
                return await resp.Content.ReadFromJsonAsync<AnalyzeResponse>(_json);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Results error");
                return null;
            }
        }
    }
}
