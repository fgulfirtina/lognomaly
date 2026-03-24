namespace LogNomaly.Web.Entities.Models;

public class UploadResponse
{
    public string SessionId { get; set; } = "";
    public string FilePath { get; set; } = "";
    public string Message { get; set; } = "";
}
