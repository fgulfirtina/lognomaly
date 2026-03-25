using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace LogNomaly.Web.Entities.Models
{
    public class AnalystFeedback
    {
        [Key]
        public int Id { get; set; }

        [Required, MaxLength(100)]
        public string LogId { get; set; } = string.Empty;

        [Required]
        public string RawLog { get; set; } = string.Empty;

        [MaxLength(100)]
        public string PredictedClass { get; set; } = string.Empty;

        [MaxLength(50)]
        public string RiskLevel { get; set; } = string.Empty;

        // "FalsePositive" veya "Investigate"
        [Required, MaxLength(50)]
        public string ActionType { get; set; } = string.Empty;

        // "Pending", "Approved", "Rejected"
        [MaxLength(50)]
        public string Status { get; set; } = "Pending";

        public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

        [Required, MaxLength(1000)]
        public string? AnalystNotes { get; set; }

        // Yapan Analist ile Bağlantı
        public int AnalystId { get; set; }
        [ForeignKey("AnalystId")]
        public Analyst? Analyst { get; set; }
        
    }
}