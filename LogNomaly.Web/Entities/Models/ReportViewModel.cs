namespace LogNomaly.Web.Entities.Models;

public class ReportViewModel
{
    public string? SessionId { get; set; }
    public AnalysisStats Stats { get; set; } = new();
    public List<AnalysisResult> Results { get; set; } = new();
    public DateTime GeneratedAt { get; set; } = DateTime.UtcNow;
}
