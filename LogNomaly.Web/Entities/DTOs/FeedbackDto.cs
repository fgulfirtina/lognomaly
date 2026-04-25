namespace LogNomaly.Web.Entities.DTOs
{
    public record FeedbackDto
    {
        public string LogId { get; init; } = string.Empty;
        public string RawLog { get; init; } = string.Empty;
        public string PredictedClass { get; init; } = string.Empty;
        public string RiskLevel { get; init; } = string.Empty;

        // "FalsePositive" or "Investigate"
        public string ActionType { get; init; } = string.Empty;
        public string? AnalystNotes { get; init; }
        public string? ProposedLabel { get; init; }
    }
}
