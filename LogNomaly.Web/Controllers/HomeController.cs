using LogNomaly.Web.ViewModels;
using LogNomaly.Web.Entities.Models;
using LogNomaly.Web.Services.Contracts;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace LogNomaly.Web.Controllers
{
    [Authorize]
    public class HomeController : Controller
    {
        private readonly IPythonApiService _api;
        private readonly ILogger<HomeController> _logger;

        public HomeController(IPythonApiService api, ILogger<HomeController> logger)
        {
            _api = api;
            _logger = logger;
        }

        // ── Dashboard ────────────────────────────────────────────────────
        public async Task<IActionResult> Index()
        {
            var vm = new DashboardViewModel();
            var sessionId = HttpContext.Session.GetString("SessionId");

            if (!string.IsNullOrEmpty(sessionId))
            {
                vm.SessionId = sessionId;
                vm.Stats = await _api.GetStatsAsync(sessionId);
                var results = await _api.GetResultsAsync(sessionId, 1, 10);
                if (results != null)
                    vm.RecentResults = results.Results;
            }

            return View(vm);
        }

        // ── Log Upload & Analyze Page ──────────────────────────────────
        public IActionResult Analyze()
        {
            return View(new AnalyzeViewModel());
        }

        [HttpPost]
        [RequestSizeLimit(52_428_800)] // 50MB
        public async Task<IActionResult> Analyze(IFormFile? logFile)
        {
            var vm = new AnalyzeViewModel();

            if (logFile == null || logFile.Length == 0)
            {
                vm.ErrorMessage = "Please Select a Log File.";
                return View(vm);
            }

            using (var stream = logFile.OpenReadStream())
            using (var reader = new StreamReader(stream))
            {
                // Read the first line for pattern check
                string? firstLine = await reader.ReadLineAsync();

                if (string.IsNullOrWhiteSpace(firstLine) ||
                   (!firstLine.Contains("blk_") && !firstLine.Contains("RAS") && !firstLine.StartsWith("-")))
                {
                    vm.ErrorMessage = "Invalid file format. Only BGL and HDFS logs are supported.";
                    return View(vm);
                }
            }

            // 1. Upload
            var uploadResp = await _api.UploadFileAsync(logFile);
            if (uploadResp == null)
            {
                vm.ErrorMessage = "Couldn't load the file. Does the Python API run?";
                return View(vm);
            }

            // 2. Analyze
            var analyzeResp = await _api.AnalyzeFileAsync(uploadResp.FilePath, uploadResp.SessionId);
            if (analyzeResp == null)
            {
                vm.ErrorMessage = "Analysis Failed.";
                return View(vm);
            }

            // Save to session
            HttpContext.Session.SetString("SessionId", uploadResp.SessionId);

            vm.SessionId = uploadResp.SessionId;
            vm.Stats = analyzeResp.Stats;
            vm.Results = analyzeResp.Results;

            return View(vm);
        }

        // ── Single Line Analyze ─────────────────────────────────────────────
        public IActionResult SingleAnalyze()
        {
            return View(new SingleAnalyzeViewModel());
        }

        [HttpPost]
        public async Task<IActionResult> SingleAnalyze(string logLine)
        {
            var vm = new SingleAnalyzeViewModel { LogLine = logLine };

            if (string.IsNullOrWhiteSpace(logLine))
            {
                vm.ErrorMessage = "Log Line cannot be null.";
                return View(vm);
            }
            if (!logLine.Contains("blk_") && !logLine.Contains("RAS") && !logLine.StartsWith("-"))
            {
                vm.ErrorMessage = "Invalid file format. Only BGL and HDFS logs are supported.";
                return View(vm);
            }

            var result = await _api.AnalyzeSingleAsync(logLine);
            if (result == null)
            {
                vm.ErrorMessage = "Couldn't load the file. Does the Python API run?";
                return View(vm);
            }

            vm.Result = result;
            return View(vm);
        }

        // ── XAI Detail ────────────────────────────────────────────────────
        public async Task<IActionResult> Xai(string sessionId, int index)
        {
            var results = await _api.GetResultsAsync(sessionId, 1, 1000);
            if (results == null || index >= results.Results.Count)
                return RedirectToAction("Analyze");

            return View(new XaiViewModel
            {
                Result = results.Results[index],
                SessionId = sessionId
            });
        }


        public async Task<IActionResult> Report(string sessionId)
        {
            if (string.IsNullOrEmpty(sessionId)) return RedirectToAction("Index");

            var stats = await _api.GetStatsAsync(sessionId);
            var results = await _api.GetResultsAsync(sessionId, 1, 100);

            var vm = new ReportViewModel
            {
                SessionId = sessionId,
                Stats = stats ?? new AnalysisStats(),
                Results = results?.Results ?? new List<AnalysisResult>()
            };

            return View(vm);
        }

        // ── API Health Check (AJAX) ─────────────────────────────────
        [HttpGet]
        public async Task<IActionResult> ApiHealth()
        {
            var health = await _api.GetHealthAsync();
            return Json(health);
        }

        [ResponseCache(Duration = 0, Location = ResponseCacheLocation.None, NoStore = true)]
        public IActionResult Error() => View();
    }
}
