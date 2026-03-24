using LogNomaly.Web.Entities.DTOs;

namespace LogNomaly.Web.Services.Contracts
{
    public interface IFeedbackService
    {
        // Geri bildirimi kaydeder, başarılıysa true döner
        Task<bool> SubmitFeedbackAsync(FeedbackDto request, int analystId);
    }
}