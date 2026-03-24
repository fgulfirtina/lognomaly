namespace LogNomaly.Web.Entities.Models;

public class AnalyzeResponse
{
    public AnalysisStats Stats { get; set; } = new();
    public List<AnalysisResult> Results { get; set; } = new();
}
