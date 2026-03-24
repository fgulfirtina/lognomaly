using LogNomaly.Web.Entities.Models;

namespace LogNomaly.Web.Services.Contracts;

public interface IPythonApiService
{
    Task<HealthResponse?> GetHealthAsync();
    Task<UploadResponse?> UploadFileAsync(IFormFile file);
    Task<AnalyzeResponse?> AnalyzeFileAsync(string filePath, string sessionId);
    Task<AnalysisResult?> AnalyzeSingleAsync(string logLine, string level = "INFO");
    Task<AnalysisStats?> GetStatsAsync(string sessionId);
    Task<AnalyzeResponse?> GetResultsAsync(string sessionId, int page = 1, int limit = 100);
}
