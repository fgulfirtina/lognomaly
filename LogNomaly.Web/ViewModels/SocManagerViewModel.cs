using LogNomaly.Web.Entities.Models;

namespace LogNomaly.Web.ViewModels
{
    public class SocManagerViewModel
    {
        // Active investigations assigned to analysts
        public List<InvestigationCase> ActiveCases { get; set; } = new List<InvestigationCase>();

        // Correction flags waiting for Senior approval
        public List<AnalystFeedback> PendingCorrections { get; set; } = new List<AnalystFeedback>();
    }
}