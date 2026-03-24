namespace LogNomaly.Web.Entities.Models;

using System.Text.Json.Serialization;

public class AnalysisResult
{
    public string Level { get; set; } = "";
    public string Message { get; set; } = "";
    public bool IsKnownThreat { get; set; }
    public string? ThreatType { get; set; }
    public string? MatchedRule { get; set; }
    public int IfPrediction { get; set; }
    public double IfAnomalyScore { get; set; }
    public string PredictedClass { get; set; } = "Normal";
    public double RfConfidence { get; set; }
    public double FinalRiskScore { get; set; }
    public string RiskLevel { get; set; } = "Low";
    public ShapExplanation? ShapExplanation { get; set; }
    [JsonPropertyName("dataset_routed")]
    public string DatasetRouted { get; set; } = string.Empty;

    [JsonPropertyName("raw_log")]
    public string RawLog { get; set; } = string.Empty;

    [JsonPropertyName("extracted_hour")]
    public int ExtractedHour { get; set; } = -1;
}
