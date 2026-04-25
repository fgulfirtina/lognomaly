namespace LogNomaly.Web.Entities.DTOs
{
    public record AssignRoleDto
    {
        public int AnalystId { get; init; }
        public string Role { get; init; } = string.Empty;
    }
}
