using LogNomaly.Web.Entities.Models;

namespace LogNomaly.Web.ViewModels
{
    public class CaseReportViewModel
    {
        public AnalystFeedback? FeedbackRecord { get; set; }
        public AnalysisResult? AiInsight { get; set; }
    }
}