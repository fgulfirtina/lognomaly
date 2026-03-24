using Microsoft.EntityFrameworkCore;
using LogNomaly.Web.Entities.Models;

namespace LogNomaly.Web.Data
{
    public class AppDbContext : DbContext
    {
        public AppDbContext(DbContextOptions<AppDbContext> options) : base(options)
        {
        }

        public DbSet<Analyst> Analysts { get; set; }
        public DbSet<AnalystFeedback> AnalystFeedbacks { get; set; }
        public DbSet<InvestigationCase> InvestigationCases { get; set; }

        protected override void OnModelCreating(ModelBuilder modelBuilder)
        {
            base.OnModelCreating(modelBuilder);

            // Vakalar ile Analistler arasındaki ilişkiyi belirtiyoruz (Cascade silinmeyi önlemek için)
            modelBuilder.Entity<InvestigationCase>()
                .HasOne(c => c.AssignedAnalyst)
                .WithMany(a => a.AssignedCases)
                .HasForeignKey(c => c.AssignedAnalystId)
                .OnDelete(DeleteBehavior.Restrict);
        }
    }
}