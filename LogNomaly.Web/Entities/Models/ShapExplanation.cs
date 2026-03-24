namespace LogNomaly.Web.Entities.Models;

public class ShapExplanation
{
    public List<ShapFeature> TopFeatures { get; set; } = new();
    public double BaseValue { get; set; }
    public string ExplanationText { get; set; } = "";
}
