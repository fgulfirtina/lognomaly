using LogNomaly.Web.Data;
using LogNomaly.Web.Entities.Models;
using LogNomaly.Web.Entities.DTOs;
using LogNomaly.Web.Services.Contracts;

namespace LogNomaly.Web.Services
{
    public class FeedbackService : IFeedbackService
    {
        private readonly AppDbContext _context;
        private readonly ILogger<FeedbackService> _logger;

        public FeedbackService(AppDbContext context, ILogger<FeedbackService> logger)
        {
            _context = context;
            _logger = logger;
        }

        public async Task<bool> SubmitFeedbackAsync(FeedbackDto request, int analystId)
        {
            try
            {
                // 1. Önce Feedback (Geri Bildirim) kaydını oluştur
                var feedback = new AnalystFeedback
                {
                    LogId = request.LogId,
                    RawLog = request.RawLog,
                    PredictedClass = request.PredictedClass,
                    RiskLevel = request.RiskLevel,
                    ActionType = request.ActionType,
                    Status = "Pending", // Karantinada, onay bekliyor
                    CreatedAt = DateTime.UtcNow,
                    AnalystId = analystId,
                    AnalystNotes = request.AnalystNotes
                };

                _context.AnalystFeedbacks.Add(feedback);
                await _context.SaveChangesAsync(); // Id'nin oluşması için önce kaydediyoruz

                // 2. Eğer analist "Investigate" dediyse, otomatik Vaka (Case) aç!
                if (request.ActionType == "Investigate")
                {
                    var newCase = new InvestigationCase
                    {
                        FeedbackId = feedback.Id, // Az önce oluşan Feedback'in ID'si
                        AssignedAnalystId = analystId, // Butona basan analistin üzerine atıyoruz
                        Status = "Open",
                        OpenedAt = DateTime.UtcNow,
                        AnalystNotes = "Auto-generated case from SOC Dashboard.",
                        ResolutionNotes = "No resolution notes are found."
                    };

                    _context.InvestigationCases.Add(newCase);
                    await _context.SaveChangesAsync();
                }

                _logger.LogInformation($"Feedback saved successfully for LogId: {request.LogId} by Analyst: {analystId}");
                return true;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, $"Error while saving feedback for LogId: {request.LogId}");
                return false;
            }
        }
    }
}