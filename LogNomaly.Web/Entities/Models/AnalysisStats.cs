namespace LogNomaly.Web.Entities.Models;
using System.Text.Json.Serialization;

public class AnalysisStats
{
    public int TotalLogs { get; set; }
    public int TotalAnomalies { get; set; }
    public double AvgRiskScore { get; set; }
    public Dictionary<string, int> RiskDistribution { get; set; } = new();
    public Dictionary<string, int> ThreatTypes { get; set; } = new();
    public double AnomalyRate { get; set; }
    [JsonPropertyName("dataset_routed")]
    public string DatasetRouted { get; set; } = string.Empty;
}
