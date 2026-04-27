using System.ComponentModel.DataAnnotations;

namespace LogNomaly.Web.Entities.DTOs
{
    public record CreateAnalystDto
    {
        [Required, MaxLength(50)]
        public string Username { get; init; } = string.Empty;
        [Required]
        public string Role { get; init; } = "Junior";
    }
}
