using LogNomaly.Web.Entities.DTOs;

namespace LogNomaly.Web.Services.Contracts
{
    public interface IFeedbackService
    {
        // Submits the feedback
        Task<bool> SubmitFeedbackAsync(FeedbackDto request, int analystId);
        Task<RetrainResponseDto> TriggerRetrainAsync();
    }
}