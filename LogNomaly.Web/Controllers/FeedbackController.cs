using LogNomaly.Web.Entities.DTOs;
using LogNomaly.Web.Services.Contracts;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using System.Security.Claims;

namespace LogNomaly.Web.Controllers
{
    [Authorize]
    public class FeedbackController : Controller
    {
        private readonly IFeedbackService _feedbackService;
        private readonly ILogger<FeedbackController> _logger;

        public FeedbackController(IFeedbackService feedbackService, ILogger<FeedbackController> logger)
        {
            _feedbackService = feedbackService;
            _logger = logger;
        }

        [HttpPost]
        public async Task<IActionResult> Submit([FromBody] FeedbackDto request)
        {
            if (request == null || string.IsNullOrEmpty(request.LogId))
            {
                _logger.LogWarning("Submit endpoint called with invalid or empty request.");
                return BadRequest(new { success = false, message = "Geçersiz veya eksik veri gönderildi." });
            }

            try
            {
                var userIdClaim = User.FindFirstValue(ClaimTypes.NameIdentifier);

                if (!int.TryParse(userIdClaim, out int actualAnalystId))
                {
                    _logger.LogWarning("Failed to extract Analyst ID from user claims.");
                    return Unauthorized(new { success = false, message = "Session invalid or expired." });
                }

                bool isSuccess = await _feedbackService.SubmitFeedbackAsync(request, actualAnalystId);

                if (isSuccess)
                {
                    return Ok(new { success = true, message = "Aksiyon başarıyla veritabanına işlendi." });
                }
                else
                {
                    return StatusCode(500, new { success = false, message = "Kayıt işlemi başarısız oldu." });
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "System error in FeedbackController Submit action.");
                return StatusCode(500, new { success = false, message = "Sistem Hatası oluştu." });
            }
        }
    }
}