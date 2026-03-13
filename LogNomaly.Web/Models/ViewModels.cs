namespace LogNomaly.Web.Models;

// ── API Response Models (Python backend ile uyumlu) ──────────────────

public class HealthResponse
{
    public string Status { get; set; } = "";
    public bool ModelsLoaded { get; set; }
    public string Version { get; set; } = "";
    public int NFeatures { get; set; }
}

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
}

public class ShapExplanation
{
    public List<ShapFeature> TopFeatures { get; set; } = new();
    public double BaseValue { get; set; }
    public string ExplanationText { get; set; } = "";
}

public class ShapFeature
{
    public string Feature { get; set; } = "";
    public double ShapValue { get; set; }
    public string Direction { get; set; } = "";
}

public class AnalysisStats
{
    public int TotalLogs { get; set; }
    public int TotalAnomalies { get; set; }
    public double AvgRiskScore { get; set; }
    public Dictionary<string, int> RiskDistribution { get; set; } = new();
    public Dictionary<string, int> ThreatTypes { get; set; } = new();
    public double AnomalyRate { get; set; }
}

public class AnalyzeResponse
{
    public AnalysisStats Stats { get; set; } = new();
    public List<AnalysisResult> Results { get; set; } = new();
}

public class UploadResponse
{
    public string SessionId { get; set; } = "";
    public string FilePath { get; set; } = "";
    public string Message { get; set; } = "";
}

// ── View Models ───────────────────────────────────────────────────────

public class DashboardViewModel
{
    public AnalysisStats? Stats { get; set; }
    public List<AnalysisResult> RecentResults { get; set; } = new();
    public string? SessionId { get; set; }
    public bool HasData => Stats != null && Stats.TotalLogs > 0;
}

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

public class XaiViewModel
{
    public AnalysisResult? Result { get; set; }
    public string? SessionId { get; set; }
}

public class SingleAnalyzeViewModel
{
    public string? LogLine { get; set; }
    public AnalysisResult? Result { get; set; }
    public string? ErrorMessage { get; set; }
}
