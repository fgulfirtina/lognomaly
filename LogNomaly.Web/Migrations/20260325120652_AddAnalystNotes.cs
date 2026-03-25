using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace LogNomaly.Web.Migrations
{
    /// <inheritdoc />
    public partial class AddAnalystNotes : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<string>(
                name: "AnalystNotes",
                table: "AnalystFeedbacks",
                type: "character varying(1000)",
                maxLength: 1000,
                nullable: false,
                defaultValue: "");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "AnalystNotes",
                table: "AnalystFeedbacks");
        }
    }
}
