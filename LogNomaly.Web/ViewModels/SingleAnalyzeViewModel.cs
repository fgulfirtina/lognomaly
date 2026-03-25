using LogNomaly.Web.Entities.Models;

namespace LogNomaly.Web.ViewModels
{
    public class SingleAnalyzeViewModel
    {
        public string? SessionId { get; set; }
        public string? LogLine { get; set; }
        public AnalysisResult? Result { get; set; }
        public string? ErrorMessage { get; set; }
        public string? FilterLevel { get; set; }
    }
}
