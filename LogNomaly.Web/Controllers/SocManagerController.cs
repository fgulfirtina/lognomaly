using LogNomaly.Web.Data;
using LogNomaly.Web.Entities.Models;
using LogNomaly.Web.Services.Contracts;
using LogNomaly.Web.ViewModels;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace LogNomaly.Web.Controllers
{
    // Only Senior Analysts can access this entire controller
    [Authorize(Roles = "Senior")]
    public class SocManagerController : Controller
    {
        private readonly AppDbContext _context;
        private readonly ILogger<SocManagerController> _logger;
        private readonly IPythonApiService _pythonApiService;

        public SocManagerController(AppDbContext context, ILogger<SocManagerController> logger, IPythonApiService pythonApiService)
        {
            _context = context;
            _logger = logger;
            _pythonApiService = pythonApiService;
        }

        [HttpGet]
        public async Task<IActionResult> Index()
        {
            var viewModel = new SocManagerViewModel
            {
                // Fetch cases with their assigned analysts and the original feedback/log
                ActiveCases = await _context.InvestigationCases
                .Include(c => c.AssignedAnalyst)
                .Include(c => c.Feedback)
                .Where(c => c.Status != "Resolved" && c.Status != "Closed")
                .OrderByDescending(c => c.OpenedAt)
                .ToListAsync(),

                // Fetch only pending false positives that need model retraining approval
                PendingFalsePositives = await _context.AnalystFeedbacks
                    .Include(f => f.Analyst)
                    .Where(f => f.ActionType == "FalsePositive" && f.Status == "Pending")
                    .OrderByDescending(f => f.CreatedAt)
                    .ToListAsync()
            };

            return View(viewModel);
        }

        [HttpPost]
        public async Task<IActionResult> ApproveFalsePositive([FromBody] int feedbackId)
        {
            try
            {
                var feedback = await _context.AnalystFeedbacks.FindAsync(feedbackId);

                if (feedback == null)
                    return NotFound(new { success = false, message = "Feedback record not found." });

                // Update status to Approved. This flags the log for the ML Retraining Pipeline.
                feedback.Status = "Approved";
                await _context.SaveChangesAsync();

                _logger.LogInformation($"False Positive #{feedbackId} APPROVED by {User.Identity?.Name} for model retraining.");

                return Ok(new { success = true, message = "False Positive approved. Added to training dataset." });
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error approving false positive.");
                return StatusCode(500, new { success = false, message = "Internal server error." });
            }
        }

        [HttpPost]
        public async Task<IActionResult> RejectFalsePositive([FromBody] int feedbackId)
        {
            try
            {
                var feedback = await _context.AnalystFeedbacks.FindAsync(feedbackId);

                if (feedback == null)
                    return NotFound(new { success = false, message = "Feedback record not found." });

                // Update status to Rejected. The model was right, the junior analyst was wrong.
                feedback.Status = "Rejected";
                await _context.SaveChangesAsync();

                _logger.LogInformation($"False Positive #{feedbackId} REJECTED by {User.Identity?.Name}.");

                return Ok(new { success = true, message = "False Positive rejected. Original AI prediction stands." });
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error rejecting false positive.");
                return StatusCode(500, new { success = false, message = "Internal server error." });
            }
        }

        [HttpGet]
        public async Task<IActionResult> Review(int id)
        {
            var feedback = await _context.AnalystFeedbacks
                .Include(f => f.Analyst)
                .FirstOrDefaultAsync(f => f.Id == id);

            if (feedback == null)
                return NotFound();

            // Logu tekrar Python yapay zekasına gönderip detaylı analiz (SHAP vb.) alıyoruz
            var aiAnalysisResult = await _pythonApiService.AnalyzeSingleAsync(feedback.RawLog);

            // Hem veritabanı kaydını hem de yapay zeka sonucunu View'a gönderiyoruz
            var viewModel = new CaseReportViewModel
            {
                FeedbackRecord = feedback,
                AiInsight = aiAnalysisResult
            };

            return View(viewModel);
        }

        [HttpPost]
        public async Task<IActionResult> CloseInvestigation([FromBody] CloseCaseRequest request)
        {
            try
            {
                // 1. Investigation Case tablosundan ilgili vakayı bul
                var invCase = await _context.InvestigationCases
                    .FirstOrDefaultAsync(c => c.FeedbackId == request.FeedbackId);

                if (invCase == null)
                    return NotFound(new { success = false, message = "Investigation case not found." });

                // 2. Statüyü güncelle ve çözülme tarihini at
                invCase.Status = "Resolved";
                invCase.ClosedAt = DateTime.UtcNow;
                invCase.ResolutionNotes = request.Notes;

                // 3. İlgili Feedback kaydının da statüsünü güncelle
                var feedback = await _context.AnalystFeedbacks.FindAsync(request.FeedbackId);
                if (feedback != null) feedback.Status = "Resolved";

                await _context.SaveChangesAsync();

                return Ok(new { success = true });
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error closing case.");
                return StatusCode(500, new { success = false, message = "Database error." });
            }
        }

        [HttpPost]
        public async Task<IActionResult> AddNotes([FromBody] CloseCaseRequest request)
        {
            try
            {
                var feedback = await _context.AnalystFeedbacks.FindAsync(request.FeedbackId);
                if (feedback == null) return NotFound(new { success = false, message = "Case not found." });

                // Mevcut notların sonuna tarih atarak yeni notu ekliyoruz
                string timeStamp = DateTime.UtcNow.ToString("dd MMM HH:mm");
                feedback.AnalystNotes += $"\n\n[{timeStamp} - Update]: {request.Notes}";

                await _context.SaveChangesAsync();
                return Ok(new { success = true });
            }
            catch (Exception ex)
            {
                return StatusCode(500, new { success = false, message = "Database error." });
            }
        }
    }
}