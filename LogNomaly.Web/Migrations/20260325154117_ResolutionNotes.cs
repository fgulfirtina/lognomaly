using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace LogNomaly.Web.Migrations
{
    /// <inheritdoc />
    public partial class ResolutionNotes : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<string>(
                name: "ResolutionNotes",
                table: "InvestigationCases",
                type: "character varying(2000)",
                maxLength: 2000,
                nullable: false,
                defaultValue: "");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "ResolutionNotes",
                table: "InvestigationCases");
        }
    }
}
