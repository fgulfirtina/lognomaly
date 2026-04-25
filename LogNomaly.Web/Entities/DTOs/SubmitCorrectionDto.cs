namespace LogNomaly.Web.Entities.DTOs
{
    public record SubmitCorrectionDto
    {
        public int FeedbackId { get; init; }
        public string ProposedLabel { get; init; } = string.Empty;
        public string AnalystNotes { get; init; } = string.Empty;
    }
}
