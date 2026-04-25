namespace LogNomaly.Web.Entities.DTOs
{
    public record ResetPasswordDto
    {
        public int AnalystId { get; init; }
        public string NewPassword { get; init; } = string.Empty;
    }
}
