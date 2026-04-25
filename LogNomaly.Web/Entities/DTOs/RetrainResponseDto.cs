namespace LogNomaly.Web.Entities.DTOs
{
    public record RetrainResponseDto
    {
        public bool Success { get; init; }
        public string Message { get; init; } = string.Empty;
        public string? Details { get; init; }
    }
}
