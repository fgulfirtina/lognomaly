namespace LogNomaly.Web.Entities.Models
{
    public class CloseCaseRequest
    {
        public int FeedbackId { get; set; }
        public string Notes { get; set; } = string.Empty;
    }
}
