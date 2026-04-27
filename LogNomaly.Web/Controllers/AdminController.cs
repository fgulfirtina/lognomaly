using LogNomaly.Web.Data;
using LogNomaly.Web.Entities.DTOs;
using LogNomaly.Web.Entities.Models;
using LogNomaly.Web.Services.Contracts;
using LogNomaly.Web.Utilities;
using LogNomaly.Web.ViewModels;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using System.Security.Claims;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace LogNomaly.Web.Controllers
{

    /// Admin-only controller. Requires "Admin" role claim.
 
    [Authorize(Roles = "Admin")]
    public class AdminController : Controller
    {
        private readonly AppDbContext _context;
        private readonly ILogger<AdminController> _logger;
        private readonly IHttpClientFactory _httpClientFactory;
        private readonly IConfiguration _configuration;
        private readonly IFeedbackService _feedbackService;

        public AdminController(
            AppDbContext context,
            ILogger<AdminController> logger,
            IHttpClientFactory httpClientFactory,
            IConfiguration configuration,
            IFeedbackService feedbackService)
        {
            _context = context;
            _logger = logger;
            _httpClientFactory = httpClientFactory;
            _configuration = configuration;
            _feedbackService = feedbackService;
        }

        // ── GET /Admin/Index ─────────────────────────────────────────
        public async Task<IActionResult> Index()
        {
            var analysts = await _context.Analysts.ToListAsync();
            var pendingFeedbacks = await _context.AnalystFeedbacks
                                        .CountAsync(f => f.Status == "Pending");
            var openCases = await _context.InvestigationCases
                                        .CountAsync(c => c.Status == "Open");
            var approvedFeedbacks = await _context.AnalystFeedbacks
                                        .CountAsync(f => f.Status == "Approved" && f.ProposedLabel != null);

            // Database health check
            bool dbOnline = false;
            try { dbOnline = await _context.Database.CanConnectAsync(); }
            catch { /* stays false */ }

            // Python API health check
            bool pythonOnline = false;
            string pythonStatus = "offline";
            try
            {
                var client = _httpClientFactory.CreateClient();
                client.Timeout = TimeSpan.FromSeconds(3);
                var pythonBase = _configuration["PythonApi:BaseUrl"] ?? "http://localhost:5000";
                var resp = await client.GetAsync($"{pythonBase}/api/health");
                if (resp.IsSuccessStatusCode)
                {
                    var body = await resp.Content.ReadAsStringAsync();
                    var json = JsonDocument.Parse(body);
                    pythonOnline = json.RootElement.GetProperty("status").GetString() == "ok";
                    bool bglLoaded = json.RootElement.TryGetProperty("bgl_loaded", out var b) && b.GetBoolean();
                    bool hdfsLoaded = json.RootElement.TryGetProperty("hdfs_loaded", out var h) && h.GetBoolean();
                    pythonStatus = pythonOnline
                        ? $"Online — BGL:{(bglLoaded ? "✓" : "✗")} HDFS:{(hdfsLoaded ? "✓" : "✗")}"
                        : "Error";
                }
            }
            catch { pythonStatus = "Unreachable"; }

            var vm = new AdminDashboardViewModel
            {
                TotalAnalysts = analysts.Count,
                JuniorAnalysts = analysts.Count(a => a.Role == "Junior"),
                SeniorAnalysts = analysts.Count(a => a.Role == "Senior"),
                PendingInvestigations = pendingFeedbacks,
                OpenCases = openCases,
                CorrectionsReadyToTrain = approvedFeedbacks,
                DatabaseOnline = dbOnline,
                PythonApiStatus = pythonStatus,
                PythonApiOnline = pythonOnline,
                Analysts = analysts
            };

            return View(vm);
        }

        // ── GET /Admin/CreateAnalyst ─────────────────────────────────
        public IActionResult CreateAnalyst() => View();

        // ── POST /Admin/CreateAnalyst ────────────────────────────────
        [HttpPost]
        [ValidateAntiForgeryToken]
        public async Task<IActionResult> CreateAnalyst(CreateAnalystDto dto)
        {
            // If there are missing fields in the form, return to Index
            if (!ModelState.IsValid)
            {
                TempData["Error"] = "Please fill in all required fields (Username, Password, Role).";
                return RedirectToAction(nameof(Index));
            }

            // If the user already exists, return to Index
            bool exists = await _context.Analysts.AnyAsync(a => a.Username == dto.Username);
            if (exists)
            {
                TempData["Error"] = $"The username '{dto.Username}' is already taken.";
                return RedirectToAction(nameof(Index));
            }

            string tempPassword = Guid.NewGuid().ToString("N").Substring(0, 6) + "X8!";

            var analyst = new Analyst
            {
                Username = dto.Username.Trim(),
                PasswordHash = PasswordHasher.HashPassword(tempPassword),
                Role = dto.Role,
                CreatedAt = DateTime.UtcNow
            };

            _context.Analysts.Add(analyst);
            await _context.SaveChangesAsync();
            _logger.LogInformation("Admin created analyst: {Username} ({Role})", analyst.Username, analyst.Role);

            TempData["Success"] = $"Analyst '{analyst.Username}' created! TEMP PASSWORD: {tempPassword} (Copy and share this securely).";
            return RedirectToAction(nameof(Index));
        }

        // ── POST /Admin/AssignRole ───────────────────────────────────
        [HttpPost]
        public async Task<IActionResult> AssignRole([FromForm] AssignRoleDto dto)
        {
            var currentUserId = int.Parse(User.FindFirstValue(ClaimTypes.NameIdentifier));

            var analyst = await _context.Analysts.FindAsync(dto.AnalystId);
            if (analyst == null)
            {
                TempData["Error"] = "Analyst not found.";
                return RedirectToAction(nameof(Index));
            }

            if (analyst.Id == currentUserId)
            {
                TempData["Error"] = "You cannot change your own role!";
                return RedirectToAction(nameof(Index));
            }

            if (dto.Role != "Junior" && dto.Role != "Senior" && dto.Role != "Admin")
            {
                TempData["Error"] = "Invalid role selected.";
                return RedirectToAction(nameof(Index));
            }

            analyst.Role = dto.Role;
            await _context.SaveChangesAsync();
            _logger.LogInformation("Admin changed role of {Username} to {Role}", analyst.Username, dto.Role);

            TempData["Success"] = $"Role for {analyst.Username} updated to {dto.Role}.";
            return RedirectToAction(nameof(Index));
        }

        // ── POST /Admin/ResetPassword ────────────────────────────────
        [HttpPost]
        public async Task<IActionResult> ResetPassword([FromForm] ResetPasswordDto dto)
        {
            string tempPassword = Guid.NewGuid().ToString("N").Substring(0, 6) + "X8!";

            var analyst = await _context.Analysts.FindAsync(dto.AnalystId);
            if (analyst == null)
                return NotFound();

            analyst.PasswordHash = PasswordHasher.HashPassword(tempPassword);
            await _context.SaveChangesAsync();

            TempData["Success"] = $"Password for analyst '{analyst.Username}' reset! TEMP PASSWORD: {tempPassword}";
            return Ok();
        }

        // ── POST /Admin/DeleteAnalyst ────────────────────────────────
        [HttpPost]
        public async Task<IActionResult> DeleteAnalyst([FromForm] int analystId)
        {
            var currentUserId = int.Parse(User.FindFirstValue(ClaimTypes.NameIdentifier));

            var analyst = await _context.Analysts
            .Include(a => a.Feedbacks)
            .Include(a => a.AssignedCases)
            .FirstOrDefaultAsync(a => a.Id == analystId);

            if (analyst == null)
            {
                TempData["Error"] = "Analyst not found.";
                return RedirectToAction(nameof(Index));
            }

            if (analyst.Id == currentUserId)
            {
                TempData["Error"] = "You cannot delete your own account!";
                return RedirectToAction(nameof(Index));
            }

            if (analyst.Role == "Admin")
            {
                TempData["Error"] = "Admin accounts cannot be deleted.";
                return RedirectToAction(nameof(Index));
            }

            if (analyst.Feedbacks.Any() || analyst.AssignedCases.Any())
            {
                TempData["Error"] = "Cannot delete analyst with existing feedback records or cases. Deactivate instead.";
                return RedirectToAction(nameof(Index));
            }

            _context.Analysts.Remove(analyst);
            await _context.SaveChangesAsync();

            TempData["Success"] = $"Analyst {analyst.Username} deleted permanently.";
            return RedirectToAction(nameof(Index));
        }

        // ── POST /Admin/TriggerRetrain ────────────────────────────────────
        [HttpPost]
        public async Task<IActionResult> TriggerRetrain()
        {
            var result = await _feedbackService.TriggerRetrainAsync();
            return Json(new { success = result.Success, message = result.Message, details = result.Details });
        }
    }
}