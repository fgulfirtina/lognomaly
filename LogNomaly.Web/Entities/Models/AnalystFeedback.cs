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

        // "FalsePositive", "Investigate", or "Correction"
        [Required, MaxLength(50)]
        public string ActionType { get; set; } = string.Empty;

        // "Pending", "Approved", "Rejected"
        [MaxLength(50)]
        public string Status { get; set; } = "Pending";

        public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

        [Required, MaxLength(1000)]
        public string? AnalystNotes { get; set; }

        // ─── Analyst's corrected label for continuous learning ───
        // Correction Type Examples:
        //   "Normal"         → False Positive (AI predicted threat, analyst says it's fine)
        //   "SQLInjection"   → False Negative (AI missed a real threat)
        //   "DDoS"           → Misclassification (AI said BruteForce, analyst says DDoS)
        [MaxLength(100)]
        public string? ProposedLabel { get; set; }

        // Navigation Properties
        public int AnalystId { get; set; }
        [ForeignKey("AnalystId")]
        public Analyst? Analyst { get; set; }
    }
}