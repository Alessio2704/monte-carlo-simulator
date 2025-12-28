const fs = require("fs");
const path = require("path");

console.log("Building ValuaScript grammar...");

const specPath = path.join(projectRoot, "language-spec.json");
const templatePath = path.join(
  projectRoot,
  "syntaxes",
  "valuascript.tmLanguage.template.json"
);
const outputPath = path.join(
  projectRoot,
  "syntaxes",
  "valuascript.tmLanguage.json"
);

try {
  const specContent = fs.readFileSync(specPath, "utf8");
  const languageSpec = JSON.parse(specContent);

  let templateContent = fs.readFileSync(templatePath, "utf8");

  const directivesRegex = languageSpec.directives
    .sort((a, b) => b.length - a.length)
    .join("|");
  const keywordsRegex = languageSpec.keywords
    .sort((a, b) => b.length - a.length)
    .join("|");
  const functionsRegex = languageSpec.functions
    .sort((a, b) => b.length - a.length)
    .join("|");
  const typesRegex = languageSpec.types
    .sort((a, b) => b.length - a.length)
    .join("|");
  const booleansRegex = languageSpec.booleans.join("|");
  const logicalOperatorsRegex = languageSpec.logical_operators.join("|");

  templateContent = templateContent.replace(/__DIRECTIVES__/g, directivesRegex);
  templateContent = templateContent.replace(/__KEYWORDS__/g, keywordsRegex);
  templateContent = templateContent.replace(/__FUNCTIONS__/g, functionsRegex);
  templateContent = templateContent.replace(/__TYPES__/g, typesRegex);
  templateContent = templateContent.replace(/__BOOLEANS__/g, booleansRegex);
  templateContent = templateContent.replace(
    /__LOGICAL_OPERATORS__/g,
    logicalOperatorsRegex
  );

  fs.writeFileSync(outputPath, templateContent);

  console.log("ValuaScript grammar built successfully!");
} catch (error) {
  console.error("Error building grammar:", error);
  process.exit(1);
}
