using LogNomaly.Web.Entities.Models;
using LogNomaly.Web.Utilities;
using Microsoft.EntityFrameworkCore;

namespace LogNomaly.Web.Data
{
    public static class DataSeeder
    {
        public static async Task SeedInitialAnalystAsync(IServiceProvider serviceProvider)
        {
            using var scope = serviceProvider.CreateScope();
            var context = scope.ServiceProvider.GetRequiredService<AppDbContext>();
            var logger = scope.ServiceProvider.GetRequiredService<ILoggerFactory>().CreateLogger("DataSeeder");

            try
            {
                // Ensures all pending migrations are applied automatically on startup
                await context.Database.MigrateAsync();

                // Check if any analysts exist in the database
                if (!await context.Analysts.AnyAsync())
                {
                    logger.LogInformation("No analysts found. Seeding the initial Admin account...");

                    var adminAnalyst = new Analyst
                    {
                        Username = "SystemAdmin",
                        // The password is now securely hashed before being saved
                        PasswordHash = PasswordHasher.HashPassword("Admin123!"),
                        Role = "Admin",
                        CreatedAt = DateTime.UtcNow
                    };

                    context.Analysts.Add(adminAnalyst);
                    await context.SaveChangesAsync();

                    logger.LogInformation("Successfully seeded the initial Senior Analyst account.");
                }
            }
            catch (Exception ex)
            {
                logger.LogError(ex, "An error occurred while seeding the database.");
                throw; // Re-throw to prevent the app from starting in an invalid state
            }
        }
    }
}