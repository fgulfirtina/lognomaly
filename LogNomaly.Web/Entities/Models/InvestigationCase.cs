using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace LogNomaly.Web.Entities.Models
{
    public class InvestigationCase
    {
        [Key]
        public int Id { get; set; }
        
        // Which feedback opened this case
        public int FeedbackId { get; set; }
        [ForeignKey("FeedbackId")]
        public AnalystFeedback? Feedback { get; set; }

        // Which analyst is assigned to the case
        public int? AssignedAnalystId { get; set; }
        [ForeignKey("AssignedAnalystId")]
        public Analyst? AssignedAnalyst { get; set; }

        // "Open", "InProgress", "Closed"
        [MaxLength(50)]
        public string Status { get; set; } = "Open";

        [Required, MaxLength(2000)]
        public string? ResolutionNotes { get; set; }

        public string? AnalystNotes { get; set; }

        public DateTime OpenedAt { get; set; } = DateTime.UtcNow;
        public DateTime? ClosedAt { get; set; }

        
    }
}