using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace LogNomaly.Web.Migrations
{
    /// <inheritdoc />
    public partial class MakeAssignedAnalystNullable : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AlterColumn<int>(
                name: "AssignedAnalystId",
                table: "InvestigationCases",
                type: "integer",
                nullable: true,
                oldClrType: typeof(int),
                oldType: "integer");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AlterColumn<int>(
                name: "AssignedAnalystId",
                table: "InvestigationCases",
                type: "integer",
                nullable: false,
                defaultValue: 0,
                oldClrType: typeof(int),
                oldType: "integer",
                oldNullable: true);
        }
    }
}
