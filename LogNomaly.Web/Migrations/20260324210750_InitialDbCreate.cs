using System;
using Microsoft.EntityFrameworkCore.Migrations;
using Npgsql.EntityFrameworkCore.PostgreSQL.Metadata;

#nullable disable

namespace LogNomaly.Web.Migrations
{
    /// <inheritdoc />
    public partial class InitialDbCreate : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "Analysts",
                columns: table => new
                {
                    Id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    Username = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    PasswordHash = table.Column<string>(type: "text", nullable: false),
                    Role = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    CreatedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Analysts", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "AnalystFeedbacks",
                columns: table => new
                {
                    Id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    LogId = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false),
                    RawLog = table.Column<string>(type: "text", nullable: false),
                    PredictedClass = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false),
                    RiskLevel = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    ActionType = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    Status = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    CreatedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: false),
                    AnalystId = table.Column<int>(type: "integer", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_AnalystFeedbacks", x => x.Id);
                    table.ForeignKey(
                        name: "FK_AnalystFeedbacks_Analysts_AnalystId",
                        column: x => x.AnalystId,
                        principalTable: "Analysts",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "InvestigationCases",
                columns: table => new
                {
                    Id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    FeedbackId = table.Column<int>(type: "integer", nullable: false),
                    AssignedAnalystId = table.Column<int>(type: "integer", nullable: false),
                    Status = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    AnalystNotes = table.Column<string>(type: "text", nullable: true),
                    OpenedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: false),
                    ClosedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_InvestigationCases", x => x.Id);
                    table.ForeignKey(
                        name: "FK_InvestigationCases_AnalystFeedbacks_FeedbackId",
                        column: x => x.FeedbackId,
                        principalTable: "AnalystFeedbacks",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "FK_InvestigationCases_Analysts_AssignedAnalystId",
                        column: x => x.AssignedAnalystId,
                        principalTable: "Analysts",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateIndex(
                name: "IX_AnalystFeedbacks_AnalystId",
                table: "AnalystFeedbacks",
                column: "AnalystId");

            migrationBuilder.CreateIndex(
                name: "IX_InvestigationCases_AssignedAnalystId",
                table: "InvestigationCases",
                column: "AssignedAnalystId");

            migrationBuilder.CreateIndex(
                name: "IX_InvestigationCases_FeedbackId",
                table: "InvestigationCases",
                column: "FeedbackId");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "InvestigationCases");

            migrationBuilder.DropTable(
                name: "AnalystFeedbacks");

            migrationBuilder.DropTable(
                name: "Analysts");
        }
    }
}
