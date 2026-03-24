namespace LogNomaly.Web.Entities.Models;

// ── API Response Models (Python backend ile uyumlu) ──────────────────

public class HealthResponse
{
    public string Status { get; set; } = "";
    public bool ModelsLoaded { get; set; }
    public string Version { get; set; } = "";
    public int NFeatures { get; set; }
}
