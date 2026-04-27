using LogNomaly.Web.Entities.Models;

namespace LogNomaly.Web.ViewModels
{
    public class AdminDashboardViewModel
    {
        public int TotalAnalysts { get; set; }
        public int JuniorAnalysts { get; set; }
        public int SeniorAnalysts { get; set; }
        public int PendingInvestigations { get; set; }
        public int OpenCases { get; set; }
        public int CorrectionsReadyToTrain { get; set; }
        public bool DatabaseOnline { get; set; }
        public string PythonApiStatus { get; set; } = string.Empty;
        public bool PythonApiOnline { get; set; }
        public List<Analyst> Analysts { get; set; } = new();
    }
}
