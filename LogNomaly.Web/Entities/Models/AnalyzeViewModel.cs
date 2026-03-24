namespace LogNomaly.Web.Entities.Models;

public class AnalyzeViewModel
{
    public string? SessionId { get; set; }
    public List<AnalysisResult> Results { get; set; } = new();
    public AnalysisStats? Stats { get; set; }
    public string? ErrorMessage { get; set; }
    public string? FilterLevel { get; set; }

    public List<AnalysisResult> FilteredResults => string.IsNullOrEmpty(FilterLevel)
        ? Results
        : Results.Where(r => r.RiskLevel == FilterLevel).ToList();
}
