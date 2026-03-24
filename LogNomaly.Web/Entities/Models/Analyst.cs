using System.ComponentModel.DataAnnotations;

namespace LogNomaly.Web.Entities.Models
{
    public class Analyst
    {
        [Key]
        public int Id { get; set; }

        [Required, MaxLength(50)]
        public string Username { get; set; } = string.Empty;

        [Required]
        public string PasswordHash { get; set; } = string.Empty;

        // "Junior" veya "Senior"
        [Required, MaxLength(20)]
        public string Role { get; set; } = "Junior";

        public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

        // Navigation Properties (Bir analistin birden çok geri bildirimi ve vakası olabilir)
        public ICollection<AnalystFeedback> Feedbacks { get; set; } = new List<AnalystFeedback>();
        public ICollection<InvestigationCase> AssignedCases { get; set; } = new List<InvestigationCase>();
    }
}