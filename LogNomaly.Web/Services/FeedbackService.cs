using LogNomaly.Web.Data;
using LogNomaly.Web.Entities.Models;
using LogNomaly.Web.Entities.DTOs;
using LogNomaly.Web.Services.Contracts;
using Microsoft.EntityFrameworkCore;
using System.Text;
using System.Text.Json;

namespace LogNomaly.Web.Services
{
    public class FeedbackService : IFeedbackService
    {
        private readonly AppDbContext _context;
        private readonly ILogger<FeedbackService> _logger;
        private readonly IHttpClientFactory _httpClientFactory;
        private readonly IConfiguration _configuration;

        public FeedbackService(
            AppDbContext context,
            ILogger<FeedbackService> logger,
            IHttpClientFactory httpClientFactory,
            IConfiguration configuration)
        {
            _context = context;
            _logger = logger;
            _httpClientFactory = httpClientFactory;
            _configuration = configuration;
        }

        public async Task<bool> SubmitFeedbackAsync(FeedbackDto request, int analystId)
        {
            try
            {
                var creator = await _context.Analysts.FindAsync(analystId);
                bool isSenior = creator != null && (creator.Role == "Senior");

                var feedback = new AnalystFeedback
                {
                    LogId = request.LogId,
                    RawLog = request.RawLog,
                    PredictedClass = request.PredictedClass,
                    RiskLevel = request.RiskLevel,
                    ActionType = request.ActionType,
                    ProposedLabel = request.ProposedLabel,
                    Status = "Pending",
                    CreatedAt = DateTime.UtcNow,
                    AnalystId = analystId,
                    AnalystNotes = request.AnalystNotes
                };

                _context.AnalystFeedbacks.Add(feedback);
                await _context.SaveChangesAsync();

                // Auto-open investigation case when requested
                if (request.ActionType == "Investigate")
                {
                    var newCase = new InvestigationCase
                    {
                        FeedbackId = feedback.Id,
                        AssignedAnalystId = isSenior ? analystId : null, // if senior opens case it is assigned to them, if junior opens the case it is in the pool
                        Status = "Open",
                        OpenedAt = DateTime.UtcNow,
                        AnalystNotes = "Auto-generated case from SOC Dashboard.",
                        ResolutionNotes = "No resolution notes are found."
                    };
                    _context.InvestigationCases.Add(newCase);
                    await _context.SaveChangesAsync();
                }

                _logger.LogInformation(
                    "Case saved for LogId: {LogId} by Analyst: {AnalystId} | ProposedLabel: {Label}",
                    request.LogId, analystId, request.ProposedLabel ?? "N/A");

                return true;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error saving case for LogId: {LogId}", request.LogId);
                return false;
            }
        }

        /// Fetches all Approved feedbacks with a ProposedLabel and POSTs them to
        /// the Python /api/retrain endpoint for continuous learning.
        public async Task<RetrainResponseDto> TriggerRetrainAsync()
        {
            // Only Approved corrections with a non-null ProposedLabel go to retraining
            var approvedCorrections = await _context.AnalystFeedbacks
                .Where(f => f.Status == "Approved" && f.ProposedLabel != null)
                .Include(f => f.Analyst)
                .Select(f => new
                {
                    f.LogId,
                    f.RawLog,
                    f.PredictedClass,
                    f.ProposedLabel,
                    f.RiskLevel,
                    f.ActionType,
                    f.AnalystNotes,
                    AnalystUsername = f.Analyst != null ? f.Analyst.Username : "unknown",
                    f.CreatedAt
                })
                .ToListAsync();

            if (!approvedCorrections.Any())
            {
                return new RetrainResponseDto
                {
                    Success = false,
                    Message = "No approved corrections found for retraining."
                };
            }

            var payload = new
            {
                corrections = approvedCorrections,
                total_count = approvedCorrections.Count,
                triggered_at = DateTime.UtcNow.ToString("o")
            };

            var pythonApiBase = _configuration["PythonApi:BaseUrl"] ?? "http://localhost:5000";
            var client = _httpClientFactory.CreateClient("PythonApi");

            try
            {
                var json = JsonSerializer.Serialize(payload);
                var content = new StringContent(json, Encoding.UTF8, "application/json");
                var response = await client.PostAsync($"{pythonApiBase}/api/retrain", content);

                var responseBody = await response.Content.ReadAsStringAsync();

                if (response.IsSuccessStatusCode)
                {
                    _logger.LogInformation(
                        "Retrain triggered successfully. Sent {Count} corrections.", approvedCorrections.Count);
                    return new RetrainResponseDto
                    {
                        Success = true,
                        Message = $"Retrain triggered with {approvedCorrections.Count} corrections.",
                        Details = responseBody
                    };
                }
                else
                {
                    _logger.LogWarning("Retrain endpoint returned {Status}: {Body}",
                        response.StatusCode, responseBody);
                    return new RetrainResponseDto
                    {
                        Success = false,
                        Message = $"Python API responded with {response.StatusCode}.",
                        Details = responseBody
                    };
                }
            }
            catch (HttpRequestException ex)
            {
                _logger.LogError(ex, "Failed to reach Python API for retrain.");
                return new RetrainResponseDto
                {
                    Success = false,
                    Message = "Could not connect to the Python AI engine.",
                    Details = ex.Message
                };
            }
        }
    }
}