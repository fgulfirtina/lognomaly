namespace LogNomaly.Web.Entities.Models;

public class SingleAnalyzeViewModel
{
    public string? LogLine { get; set; }
    public AnalysisResult? Result { get; set; }
    public string? ErrorMessage { get; set; }
}
